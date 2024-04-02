from django.db import models
from spacy import blank
from traitlets import default
from champion_backend.settings import EMAIL_HOST_USER
from main.enums import MATCH_RESULT, MATCH_STATUS
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


class MatchParticipant(models.Model):
    participant = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.IntegerField(default=0, verbose_name='Счет')
    result = models.PositiveSmallIntegerField(choices=MATCH_RESULT, null=True, blank=True, verbose_name='Результат')

    class Meta:
        verbose_name = 'Участник матча'
        verbose_name_plural = 'Участники матчей'

    def __str__(self):
        return f"Участник {self.participant}"


class Match(models.Model):
    scheduled_start = models.DateTimeField(verbose_name='Запланированное время начала')
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое время начала')
    duration = models.DurationField(null=True, blank=True, verbose_name='Продолжительность')
    status = models.PositiveSmallIntegerField(choices=MATCH_STATUS, default=0, verbose_name='Статус')
    winner = models.ForeignKey(MatchParticipant, on_delete=models.SET_NULL, null=True, related_name='won_matches', verbose_name='Победитель')
    participants = models.ManyToManyField(MatchParticipant, related_name='tournament_participants', verbose_name='Участники турнира')
    
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
    participants = models.ManyToManyField(User, related_name='participants_tournament', verbose_name='Участники')
    requests = models.ManyToManyField(User, related_name='requests_tournament', verbose_name='Запросы на участие')
    teams = models.ManyToManyField(Team, related_name='tournaments', verbose_name='Команды')
    max_participants = models.IntegerField(default=4, verbose_name='Максимальное количество участников')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    photo = models.ImageField(upload_to='tournaments_photos/', blank=True, null=True)
    stages = models.ManyToManyField(TournamentStage, related_name='stages', verbose_name='Этапы турнира')

    class Meta:
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return self.name


class New(models.Model):
    text = models.TextField(verbose_name='Текст')
    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='news', verbose_name='Турнир')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return f"Новость {self.id}"
