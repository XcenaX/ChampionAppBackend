from django.db import models
from django.contrib.auth.models import AbstractUser
from main.enums import *
from main.managers import CustomUserManager
from main.all_models.sport import Sport

class User(AbstractUser):
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=0, verbose_name='Роль')
    email_code = models.CharField(max_length=5, blank=True, verbose_name='Email Код')
    interested_sports = models.ManyToManyField(Sport, verbose_name='Интересующие виды спорта')
    avatar = models.ImageField(upload_to='users_avatars/', verbose_name='Аватары', blank=True, null=True)
    degree = models.PositiveSmallIntegerField(choices=DEGREE_CHOICES, default=0, verbose_name='Уровень мастерства')
    rating = models.IntegerField(default=0, verbose_name='Рейтинг')
    google = models.TextField(blank=True, verbose_name='Google')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    surname = models.CharField(max_length=100, blank=True, verbose_name='Фамилия')
    notify = models.BooleanField(default=False, verbose_name='Уведомлять ли юзера')
    active_subscription = models.OneToOneField(
        'Subscription',
        on_delete=models.SET_NULL,
        related_name='user_active_subscription',
        null=True,
        blank=True,
        verbose_name='Активная подписка'
    )
    date_payment = models.DateField(null=True, blank=True, verbose_name='Дата последнего платежа')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username