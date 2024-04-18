import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'champion_backend.settings')

app = Celery('champion_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = { # Пример что можно сделать в будущем
    # 'renew-subs': {
    #     'task': 'api.tasks.subs_auto_renew',
    #     'schedule': crontab(hour='12')
    # },
    # 'send-notif-task': {
    #     'task': 'api.tasks.start_push_mailing',
    #     'schedule': crontab(minute='*/5')
    # },    
}
