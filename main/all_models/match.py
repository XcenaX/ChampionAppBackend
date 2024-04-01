from django.db import models
from spacy import blank
from traitlets import default
from main.all_models.tournament import TournamentStage
from main.models import User
from main.all_models.sport import Sport
from main.enums import *


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
    lat = models.FloatField(blank=True, null=True)
    lon = models.FloatField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_amateur_matches')
    participants = models.ManyToManyField(User, related_name='opponents_amateur_matches')
    requests = models.ManyToManyField(User, related_name='requests_amateur_matches')
    max_participants = models.IntegerField(default=1)
    auto_accept_participants = models.BooleanField(default=False)
    enter_price = models.IntegerField()
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта')

    class Meta:
        verbose_name = 'Любительский матч'
        verbose_name_plural = 'Любительские матчи'

    def __str__(self):
        return f"Матч: {self.name}"
