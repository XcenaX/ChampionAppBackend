from django.core.files.base import ContentFile
import base64
import uuid


def _decode_photo(self, photo_base64):
        format, imgstr = photo_base64.split(';base64,')
        ext = format.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")