from django.apps import AppConfig
import redis
from django.conf import settings


redis_instance = redis.StrictRedis(
    host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
