from django.db import models
from champion_backend.settings import EMAIL_HOST_USER
from main.models import User
from main.all_models.sport import Sport
from main.all_models.team import Team

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


class New(models.Model):
    text = models.TextField(verbose_name='Текст')
    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='news', verbose_name='Турнир')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return f"Новость {self.id}"
