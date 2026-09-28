import os
import requests
from django.conf import settings

class TelegramService:
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_STORAGE_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.file_url = f"https://api.telegram.org/file/bot{self.bot_token}"

    def upload_file(self, file_path, mime_type="application/octet-stream", filename=None):
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_STORAGE_CHAT_ID missing in settings.")

        filename = filename or os.path.basename(file_path)
        url = f"{self.base_url}/sendDocument"

        with open(file_path, 'rb') as f:
            files = {'document': (filename, f, mime_type)}
            data = {'chat_id': self.chat_id, 'caption': f"☁️ Telenary Asset: {filename}"}
            resp = requests.post(url, data=data, files=files, timeout=120)
            resp.raise_for_status()

            res = resp.json()
            if not res.get('ok'):
                raise RuntimeError(f"Telegram upload failed: {res.get('description')}")

            doc = res['result']['document']
            return {
                'file_id': doc['file_id'],
                'message_id': res['result']['message_id'],
                'file_size': doc.get('file_size', os.path.getsize(file_path)),
                'mime_type': doc.get('mime_type', mime_type)
            }

    def get_file_url(self, file_id):
        url = f"{self.base_url}/getFile"
        resp = requests.get(url, params={'file_id': file_id}, timeout=15)
        resp.raise_for_status()
        res = resp.json()
        if not res.get('ok'):
            raise RuntimeError(f"Telegram getFile error: {res.get('description')}")
        return f"{self.file_url}/{res['result']['file_path']}"

    def stream_file(self, file_id, headers=None):
        download_url = self.get_file_url(file_id)
        req_headers = {}
        if headers and 'HTTP_RANGE' in headers:
            req_headers['Range'] = headers['HTTP_RANGE']
        return requests.get(download_url, headers=req_headers, stream=True, timeout=60)
