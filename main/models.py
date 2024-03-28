import random
import string
from django.db import models
from django.contrib.auth.models import AbstractUser
from traitlets import default
from main.enums import *
from main.managers import CustomUserManager
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from champion_backend.settings import EMAIL_HOST_USER
from django.contrib import admin


class Sport(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    image = models.ImageField(upload_to='sports_images/', default='default_sport.jpg', verbose_name='Изображение')

    class Meta:
        verbose_name = 'Вид спорта'
        verbose_name_plural = 'Виды спорта'

    def __str__(self):
        return self.name
    

class Confirmation(models.Model):
    email = models.CharField(max_length=100, default='')
    code = models.CharField(max_length=6, default='')

    def save(self, *args, **kwargs):
        """Генерируем код"""
        if not self.code:
            for confirmation in Confirmation.objects.filter(email=self.email):
                confirmation.delete()

            letters = string.digits
            code_length = 6
            random_str = ''.join(random.choice(letters) for i in range(code_length))
            self.code = random_str
            try:
                html_message = render_to_string('confirm_code.html', {'code': random_str})
                plain_message = strip_tags(html_message)
                send_mail(
                    "Подтверждение почты",
                    plain_message,
                    EMAIL_HOST_USER,
                    [self.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                # email = EmailMessage('Подтверждение почты', "Для подтверждения вашей почты введите этот код: <h2>{0}</h2>".format(random_str), to=[self.email])
                # email.send()
            except Exception as e:
                print("ОШИБКА ПРИ ОТПРАВКЕ EMAIL: ", e)

        super().save(*args, **kwargs)
    
    @admin.display(description='Почта')
    def email_display(self):
        return self.email
    
    @admin.display(description='Код подтверждения')
    def code_display(self):
        return self.code
    

class User(AbstractUser):
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICES, default=0, verbose_name='Роль')
    email_code = models.CharField(max_length=5, blank=True, verbose_name='Email Код')
    interested_sports = models.ManyToManyField(Sport, verbose_name='Интересующие виды спорта')
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

class Team(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    logo = models.ImageField(upload_to='team_logos/', default='default_logo.jpg', verbose_name='Логотип')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'

    def __str__(self):
        return self.name

class TeamMemberRole(models.Model):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта')
    name = models.CharField(max_length=255, verbose_name='Название роли')

    class Meta:
        verbose_name = 'Роль в команде'
        verbose_name_plural = 'Роли в командах'

    def __str__(self):
        return self.name

class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members', verbose_name='Команда')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    role = models.ForeignKey(TeamMemberRole, on_delete=models.CASCADE, verbose_name='Роль')

    class Meta:
        verbose_name = 'Член команды'
        verbose_name_plural = 'Члены команд'

class TournamentPlace(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')

    class Meta:
        verbose_name = 'Место проведения турнира'
        verbose_name_plural = 'Места проведения турниров'

    def __str__(self):
        return self.name


class Tournament(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_tournaments', verbose_name='Владелец')
    place = models.ForeignKey(TournamentPlace, on_delete=models.CASCADE, related_name='tournaments', verbose_name='Место проведения')
    description = models.TextField(verbose_name='Описание')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта')
    enter_price = models.IntegerField(verbose_name='Цена участия')
    prize_pool = models.IntegerField(verbose_name='Призовой фонд')
    rules = models.TextField(verbose_name='Правила')
    users = models.ManyToManyField(User, related_name='tournaments', verbose_name='Участники')
    teams = models.ManyToManyField(Team, related_name='tournaments', verbose_name='Команды')
    max_participants_amount = models.IntegerField(default=4, verbose_name='Максимальное количество участников')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return self.name


class TournamentStage(models.Model):
    start = models.DateTimeField(verbose_name='Начало этапа')
    name = models.CharField(max_length=255, verbose_name='Название этапа')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='stages', verbose_name='Турнир')

    class Meta:
        verbose_name = 'Этап турнира'
        verbose_name_plural = 'Этапы турниров'

    def __str__(self):
        return f"{self.name} ({self.tournament.name})"


class Match(models.Model):
    tournament_stage = models.ForeignKey(TournamentStage, on_delete=models.CASCADE, related_name='matches', verbose_name='Этап турнира')
    scheduled_start = models.DateTimeField(verbose_name='Запланированное время начала')
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое время начала')
    duration = models.DurationField(null=True, blank=True, verbose_name='Продолжительность')
    status = models.PositiveSmallIntegerField(choices=MATCH_STATUS, default=0, verbose_name='Статус')
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='won_matches', verbose_name='Победитель')

    class Meta:
        verbose_name = 'Матч'
        verbose_name_plural = 'Матчи'

    def __str__(self):
        return f"Матч {self.id} ({self.tournament_stage.tournament.name})"


class MatchParticipant(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='participants')
    participant = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0, verbose_name='Счет')
    result = models.PositiveSmallIntegerField(choices=MATCH_RESULT, null=True, blank=True, verbose_name='Результат')

    class Meta:
        verbose_name = 'Участник матча'
        verbose_name_plural = 'Участники матчей'

    def __str__(self):
        return f"Участник {self.participant} в матче {self.match}"


class AmateurMatch(models.Model):
    name = models.CharField(max_length=255)
    start = models.DateTimeField()
    address = models.CharField(max_length=255)
    lat = models.FloatField()
    lon = models.FloatField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_amateur_matches')
    opponent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='opponent_amateur_matches')
    enter_price = models.IntegerField()

    class Meta:
        verbose_name = 'Любительский матч'
        verbose_name_plural = 'Любительские матчи'

    def __str__(self):
        return f"Матч: {self.name}"

class New(models.Model):
    text = models.TextField(verbose_name='Текст')
    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='news', verbose_name='Турнир')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return f"Новость {self.id}"


class CourtFacility(models.Model):
    text = models.TextField(verbose_name='Описание')

    class Meta:
        verbose_name = 'Удобство площадки'
        verbose_name_plural = 'Удобства площадок'

    def __str__(self):
        return self.text
    

class Court(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_courts', verbose_name='Владелец')
    name = models.CharField(max_length=255, verbose_name='Название')
    address = models.CharField(max_length=255, verbose_name='Адрес')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    facilities = models.ManyToManyField(CourtFacility, related_name='courts', verbose_name='Удобства')

    class Meta:
        verbose_name = 'Корт'
        verbose_name_plural = 'Корты'

    def __str__(self):
        return self.name

class CourtReview(models.Model):
    star = models.IntegerField(verbose_name='Рейтинг')
    text = models.TextField(verbose_name='Отзыв')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='court_reviews', verbose_name='Пользователь')
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='reviews', verbose_name='Площадка')

    class Meta:
        verbose_name = 'Отзыв о площадке'
        verbose_name_plural = 'Отзывы о площадках'

    def __str__(self):
        return f'Отзыв от {self.user} - {self.star} звезд'

class CourtBook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='court_books', verbose_name='Пользователь')
    start = models.DateTimeField(verbose_name='Начало бронирования')
    court = models.ForeignKey(Court, on_delete=models.CASCADE, related_name='bookings', verbose_name='Площадка')

    class Meta:
        verbose_name = 'Бронирование площадки'
        verbose_name_plural = 'Бронирования площадок'

    def __str__(self):
        return f'Бронирование от {self.user} для {self.court}'

class Plan(models.Model):
    name = models.CharField(
        max_length=255, verbose_name='Наименование')
    price_month = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name='Цена (в месяц)')
    price_half_year = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name='Цена (в полгода)')
    price_year = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name='Цена (в год)')

    class Meta:
        verbose_name = 'План подписки'
        verbose_name_plural = 'Планы подписок'

    def __str__(self):
        return self.name
    

class Subscription(models.Model):    
    plan = models.ForeignKey(
        Plan,
        on_delete=models.RESTRICT,
        related_name='subscriptions',
        verbose_name='План'
    )
    is_monthly = models.BooleanField(
        null=False,
        default=True,
        verbose_name='Ежемесечная подписка'
    )    
    start_date = models.DateTimeField(verbose_name='Начало действия')
    end_date = models.DateTimeField(verbose_name='Конец действия')
    is_auto_renew = models.BooleanField(
        default=True, verbose_name='Автопродление')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return str(self.id)


class Transaction(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.RESTRICT,
        related_name='transaction',
        verbose_name='Подписка',
        null=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Сумма')
    type = models.PositiveSmallIntegerField(verbose_name='Тип')
    date_time = models.DateTimeField(verbose_name='Дата совершения')
    is_paid = models.BooleanField(default=False, verbose_name='Завершена')

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'

    def __str__(self):
        if self.user:
            return f'{self.user.id} - {self.date_time}'
        return f'Транзакция от {self.date_time}'