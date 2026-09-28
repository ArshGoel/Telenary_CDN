import uuid
from django.db import models
from django.utils import timezone

class ApiKey(models.Model):
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"

class MediaAsset(models.Model):
    RESOURCE_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
        ('raw', 'Raw Document'),
        ('audio', 'Audio'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.CharField(max_length=255, unique=True, db_index=True)
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    file_hash = models.CharField(max_length=64, unique=True)  # SHA-256 deduplication
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES, default='image')
    format = models.CharField(max_length=20, blank=True)

    # Dimensions & Audio/Video
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)

    # Telegram References
    telegram_file_id = models.CharField(max_length=255)
    telegram_message_id = models.BigIntegerField()
    local_thumb_path = models.CharField(max_length=255, blank=True, null=True)

    folder = models.CharField(max_length=100, default='root')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.public_id}.{self.format}"

    def to_cloudinary_dict(self, request=None):
        host = request.build_absolute_uri('/')[:-1] if request else ""
        return {
            'public_id': self.public_id,
            'filename': self.file_name,
            'format': self.format,
            'resource_type': self.resource_type,
            'bytes': self.file_size,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'folder': self.folder,
            'url': f"{host}/api/v1/media/{self.id}/stream",
            'secure_url': f"{host}/api/v1/media/{self.id}/stream",
            'thumbnail_url': f"{host}/api/v1/media/{self.id}/thumbnail",
            'transform_url': f"{host}/api/v1/media/{self.id}/transform?w=400&h=400&q=80&fmt=webp",
            'created_at': self.created_at.isoformat(),
        }
