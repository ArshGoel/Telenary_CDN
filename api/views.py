import os
import json
import tempfile
from PIL import Image
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from api.models import MediaAsset, ApiKey
from api.services.telegram_service import TelegramService
from api.services.media_processor import TelenaryProcessor

def dashboard_view(request):
    """Developer Dashboard & Media Portal View."""
    total_assets = MediaAsset.objects.count()
    api_keys = list(ApiKey.objects.values('id', 'name', 'key', 'created_at'))
    return render(request, 'dashboard.html', {
        'total_assets': total_assets,
        'api_keys': api_keys
    })

@csrf_exempt
def api_v1_upload(request):
    """
    Cloudinary-Compatible REST Upload Endpoint.
    POST /api/v1/upload
    Form Params: file (multipart file), public_id (optional), folder (optional)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)

    files = request.FILES.getlist('file') or request.FILES.getlist('files')
    public_id = request.POST.get('public_id')
    folder = request.POST.get('folder', 'root')

    if not files:
        return JsonResponse({'error': 'No file parameter attached in form-data'}, status=400)

    processor = TelenaryProcessor()
    temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
    os.makedirs(temp_dir, exist_ok=True)

    results = []

    for uploaded_file in files:
        temp_file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_file_path, 'wb+') as dest:
            for chunk in uploaded_file.chunks():
                dest.write(chunk)

        try:
            asset, created = processor.process_and_store(
                temp_file_path,
                original_filename=uploaded_file.name,
                public_id=public_id,
                folder=folder
            )
            results.append(asset.to_cloudinary_dict(request))
        finally:
            if os.path.exists(temp_file_path):
                import gc, time
                gc.collect()
                try:
                    os.remove(temp_file_path)
                except Exception:
                    pass

    if len(results) == 1:
        return JsonResponse(results[0])
    return JsonResponse({'resources': results, 'count': len(results)})

def api_v1_resources(request):
    """List resources in Cloudinary format."""
    query = request.GET.get('q', '').strip()
    resource_type = request.GET.get('resource_type')

    queryset = MediaAsset.objects.all()
    if resource_type:
        queryset = queryset.filter(resource_type=resource_type)
    if query:
        queryset = queryset.filter(public_id__icontains=query)

    items = [asset.to_cloudinary_dict(request) for asset in queryset]
    return JsonResponse({'resources': items, 'total_count': len(items)})

@csrf_exempt
def api_v1_resource_detail(request, asset_id):
    """GET single asset metadata or DELETE asset."""
    asset = get_object_or_404(MediaAsset, id=asset_id)
    if request.method == 'DELETE':
        asset.delete()
        return JsonResponse({'success': True, 'message': f'Asset {asset_id} deleted.'})
    return JsonResponse(asset.to_cloudinary_dict(request))

def api_v1_stream(request, asset_id):
    """High-speed CDN streaming proxy for photos, videos, and documents."""
    asset = get_object_or_404(MediaAsset, id=asset_id)
    tg_service = TelegramService()

    try:
        tg_response = tg_service.stream_file(asset.telegram_file_id, headers=request.META)
        
        response = StreamingHttpResponse(
            tg_response.iter_content(chunk_size=65536),
            content_type=asset.mime_type or 'application/octet-stream',
            status=tg_response.status_code
        )
        
        if 'Content-Length' in tg_response.headers:
            response['Content-Length'] = tg_response.headers['Content-Length']
        if 'Content-Range' in tg_response.headers:
            response['Content-Range'] = tg_response.headers['Content-Range']

        response['Content-Disposition'] = f'inline; filename="{asset.file_name}"'
        response['Accept-Ranges'] = 'bytes'
        response['Cache-Control'] = 'public, max-age=31536000'
        return response
    except Exception as e:
        return HttpResponse(f"CDN streaming error: {e}", status=500)

def api_v1_thumbnail(request, asset_id):
    """Serve cached WebP thumbnail."""
    asset = get_object_or_404(MediaAsset, id=asset_id)
    if asset.local_thumb_path:
        full_thumb = os.path.join(settings.MEDIA_ROOT, asset.local_thumb_path)
        if os.path.exists(full_thumb):
            with open(full_thumb, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/webp')

    return api_v1_stream(request, asset_id)

def api_v1_transform(request, asset_id):
    """
    Dynamic Image Resizing & Format Converter Proxy.
    GET /api/v1/media/<id>/transform?w=400&h=400&q=80&fmt=webp
    """
    asset = get_object_or_404(MediaAsset, id=asset_id)
    if asset.resource_type != 'image':
        return api_v1_stream(request, asset_id)

    try:
        width = int(request.GET.get('w', 0))
        height = int(request.GET.get('h', 0))
        quality = int(request.GET.get('q', 80))
        fmt = request.GET.get('fmt', 'webp').lower()
    except ValueError:
        width = height = 0
        quality = 80
        fmt = 'webp'

    if width <= 0 and height <= 0:
        return api_v1_stream(request, asset_id)

    cache_dir = os.path.join(settings.MEDIA_ROOT, 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{asset.id}_w{width}_h{height}_q{quality}.{fmt}")

    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return HttpResponse(f.read(), content_type=f'image/{fmt}')

    source_path = None
    if asset.local_thumb_path:
        full_thumb = os.path.join(settings.MEDIA_ROOT, asset.local_thumb_path)
        if os.path.exists(full_thumb):
            source_path = full_thumb

    if not source_path:
        return api_v1_stream(request, asset_id)

    try:
        with Image.open(source_path) as img:
            img = img.convert('RGB')
            w = width or img.width
            h = height or img.height
            img.thumbnail((w, h))
            img.save(cache_file, fmt.upper(), quality=quality)
            img.close()

        with open(cache_file, 'rb') as f:
            return HttpResponse(f.read(), content_type=f'image/{fmt}')
    except Exception:
        return api_v1_stream(request, asset_id)

@csrf_exempt
def api_v1_keys(request):
    """API Key Management Endpoint."""
    if request.method == 'GET':
        keys = list(ApiKey.objects.values('id', 'name', 'key', 'created_at'))
        return JsonResponse({'keys': keys})
    elif request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name', 'My Project').strip()
        new_key = ApiKey.objects.create(name=name)
        return JsonResponse({'id': new_key.id, 'name': new_key.name, 'key': new_key.key})
