from datetime import datetime
import math
from django.db import models
from spacy import blank
from traitlets import default
from champion_backend.settings import EMAIL_HOST_USER
from main.enums import MATCH_RESULT, MATCH_STATUS, TOURNAMENT_TYPE
from main.models import User
from main.all_models.sport import Sport
from main.all_models.team import Team

from django.db.models.signals import pre_delete
from django.dispatch import receiver

class TournamentPlace(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')

    class Meta:
        verbose_name = 'Место проведения турнира'
        verbose_name_plural = 'Места проведения турниров'

    def __str__(self):
        return self.name


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=True, null=True)
    score = models.IntegerField(default=0, verbose_name='Счет')
    result = models.PositiveSmallIntegerField(choices=MATCH_RESULT, null=True, blank=True, verbose_name='Результат')

    class Meta:
        verbose_name = 'Участник матча'
        verbose_name_plural = 'Участники матчей'

    def __str__(self):
        if self.user:
            return f"Участник {self.user}"
        else:
            return f"Участник {self.team}"

class Match(models.Model):
    scheduled_start = models.DateTimeField(verbose_name='Запланированное время начала', blank=True, null=True)
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое время начала')
    duration = models.DurationField(null=True, blank=True, verbose_name='Продолжительность')
    status = models.PositiveSmallIntegerField(choices=MATCH_STATUS, default=0, verbose_name='Статус')
    winner = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='won_matches', verbose_name='Победитель')
    # participants = models.ManyToManyField(Participant, related_name='tournament_participants', verbose_name='Участники турнира')
    participant1 = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="match_participant1", blank=True, null=True, verbose_name="Участник 1")
    participant2 = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="match_participant2", blank=True, null=True, verbose_name="Участник 2")
    
    class Meta:
        verbose_name = 'Матч'
        verbose_name_plural = 'Матчи'

    def __str__(self):
        return f"Матч {self.id}"
    

class TournamentStage(models.Model):
    start = models.DateTimeField(verbose_name='Начало этапа', blank=True, null=True,)
    end = models.DateTimeField(verbose_name='Окончание этапа', blank=True, null=True,)
    name = models.CharField(max_length=255, verbose_name='Название этапа')
    matches = models.ManyToManyField(Match, related_name='stage_matches', verbose_name='Матчи этапа турнира')

    def delete(self, *args, **kwargs):
        self.matches.all().delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = 'Этап турнира'
        verbose_name_plural = 'Этапы турниров'

    def __str__(self):
        return f"{self.name}"


class Tournament(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_tournaments', verbose_name='Владелец')
    place = models.ForeignKey(TournamentPlace, on_delete=models.CASCADE, related_name='tournaments', verbose_name='Место проведения')
    description = models.TextField(verbose_name='Описание', default="")
    start = models.DateTimeField(verbose_name='Дата и время начала регистрации', blank=True, null=True)
    end = models.DateTimeField(verbose_name='Дата и время окончания регистрации', blank=True, null=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта')
    enter_price = models.IntegerField(verbose_name='Цена участия')
    prize_pool = models.IntegerField(verbose_name='Призовой фонд')
    rules = models.TextField(verbose_name='Правила', default="")
    participants = models.ManyToManyField(Participant, related_name='participants_tournament', verbose_name='Участники')
    requests = models.ManyToManyField(User, related_name='requests_tournament', verbose_name='Запросы на участие')
    teams = models.ManyToManyField(Team, related_name='tournaments', verbose_name='Команды')
    max_participants = models.IntegerField(default=4, verbose_name='Максимальное количество участников')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    photo = models.ImageField(upload_to='tournaments_photos/', blank=True, null=True)
    stages = models.ManyToManyField(TournamentStage, related_name='stages', verbose_name='Этапы турнира')
    bracket = models.PositiveSmallIntegerField(choices=TOURNAMENT_TYPE, null=True, blank=True, verbose_name='Тип сетки турнира')

    class Meta:
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return self.name
    
    def delete(self, *args, **kwargs):
        self.stages.all().delete()
        self.participants.all().delete()
        super().delete(*args, **kwargs)


class New(models.Model):
    text = models.TextField(verbose_name='Текст')
    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='news', verbose_name='Турнир')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return f"Новость {self.id}"

@receiver(pre_delete, sender=Tournament)
def delete_related_stages(sender, instance, **kwargs):
    instance.stages.all().delete()
    instance.participants.all().delete()

@receiver(pre_delete, sender=TournamentStage)
def delete_related_stages(sender, instance, **kwargs):
    instance.matches.all().delete()