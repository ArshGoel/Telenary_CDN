import os
import hashlib
import mimetypes
import logging
from pathlib import Path
from PIL import Image
from django.conf import settings
from api.models import MediaAsset
from api.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

SUPPORTED_IMAGES = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic', '.gif', '.svg', '.tiff'}
SUPPORTED_VIDEOS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv', '.m4v'}
SUPPORTED_AUDIO = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac'}

def get_file_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

def classify_resource_type(file_path, mime_type=""):
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_IMAGES or 'image' in (mime_type or ''):
        return 'image'
    elif ext in SUPPORTED_VIDEOS or 'video' in (mime_type or ''):
        return 'video'
    elif ext in SUPPORTED_AUDIO or 'audio' in (mime_type or ''):
        return 'audio'
    return 'raw'

def generate_local_thumbnail(file_path, asset_id):
    thumbs_dir = Path(settings.MEDIA_ROOT) / 'thumbnails'
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumbs_dir / f"{asset_id}.webp"
    rel_thumb_path = f"thumbnails/{asset_id}.webp"

    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in SUPPORTED_IMAGES:
            with Image.open(file_path) as img:
                img.thumbnail((450, 450))
                img_rgb = img.convert('RGB')
                img_rgb.save(thumb_path, 'WEBP', quality=85)
                img_rgb.close()
                img.close()
            return rel_thumb_path
    except Exception as e:
        logger.error(f"Thumbnail error: {e}")
    return None

class TelenaryProcessor:
    def __init__(self):
        self.telegram_service = TelegramService()

    def process_and_store(self, file_path, original_filename=None, public_id=None, folder='root'):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = original_filename or os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_hash = get_file_sha256(file_path)

        # Check for deduplication
        existing = MediaAsset.objects.filter(file_hash=file_hash).first()
        if existing:
            return existing, False

        guessed_type, _ = mimetypes.guess_type(file_path)
        mime_type = guessed_type or 'application/octet-stream'
        resource_type = classify_resource_type(file_path, mime_type)
        ext_format = os.path.splitext(file_name)[1].lstrip('.').lower()

        # Image dimensions if applicable
        width, height = None, None
        if resource_type == 'image':
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    img.close()
            except Exception:
                pass

        # Upload to Telegram Cloud Storage
        tg_res = self.telegram_service.upload_file(file_path, mime_type=mime_type, filename=file_name)

        clean_pub_id = public_id or os.path.splitext(file_name)[0]
        # Guarantee unique public_id
        if MediaAsset.objects.filter(public_id=clean_pub_id).exists():
            clean_pub_id = f"{clean_pub_id}_{file_hash[:8]}"

        asset = MediaAsset.objects.create(
            public_id=clean_pub_id,
            file_name=file_name,
            file_size=file_size,
            mime_type=mime_type,
            file_hash=file_hash,
            resource_type=resource_type,
            format=ext_format,
            width=width,
            height=height,
            telegram_file_id=tg_res['file_id'],
            telegram_message_id=tg_res['message_id'],
            folder=folder
        )

        thumb_rel = generate_local_thumbnail(file_path, str(asset.id))
        if thumb_rel:
            asset.local_thumb_path = thumb_rel
            asset.save(update_fields=['local_thumb_path'])

        return asset, True
