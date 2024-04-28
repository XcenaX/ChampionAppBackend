from django.db import models
from main.enums import MATCH_STATUS, TOURNAMENT_TYPE, TOURNAMENT_BRACKET_TYPE
from main.models import User
from main.all_models.sport import Sport
from main.all_models.team import Team

from django.db.models.signals import pre_delete
from django.dispatch import receiver
 

class Tournament(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название', db_index=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_tournaments', verbose_name='Владелец')
    city = models.TextField(verbose_name='Город', default="")    
    description = models.TextField(verbose_name='Описание', default="")
    start = models.DateTimeField(verbose_name='Дата и время начала регистрации', blank=True, null=True, db_index=True)
    end = models.DateTimeField(verbose_name='Дата и время окончания регистрации', blank=True, null=True, db_index=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта', db_index=True)
    enter_price = models.IntegerField(verbose_name='Цена участия', db_index=True)
    prize_pool = models.IntegerField(verbose_name='Призовой фонд')
    rules = models.TextField(verbose_name='Правила', default="")
    users_requests = models.ManyToManyField(User, related_name='users_requests_tournament', verbose_name='Инливидуальные запросы на участие')
    teams_requests = models.ManyToManyField(Team, related_name='_teams_requests_tournament', verbose_name='Командные запросы на участие')
    moderators = models.ManyToManyField(User, related_name='moderators_tournament', verbose_name='Модераторы турнира')
    max_participants = models.IntegerField(default=4, verbose_name='Максимальное количество участников')
    max_team_size = models.IntegerField(blank=True, null=True, verbose_name='Максимальное количество участников в команде')
    min_team_size = models.IntegerField(blank=True, null=True, verbose_name='Минимальное количество участников в команде')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    bracket = models.PositiveSmallIntegerField(choices=TOURNAMENT_BRACKET_TYPE, null=True, blank=True, verbose_name='Тип сетки турнира')
    tournament_type = models.PositiveSmallIntegerField(choices=TOURNAMENT_TYPE, null=True, blank=True, verbose_name='Тип турнира')  
    verified = models.BooleanField(default=False, verbose_name='Подтверждено модератором')
    auto_accept_participants = models.BooleanField(default=False, verbose_name='Автоматически принимать всех')
    allow_not_full_teams = models.BooleanField(default=False, verbose_name='Разрешить участвовать командам с неполными составами')
    is_team_tournament = models.BooleanField(default=False, verbose_name='Командный турнир')

    # Swiss
    win_points = models.FloatField(blank=True, null=True, verbose_name='Очки за победу')
    draw_points = models.FloatField(blank=True, null=True, verbose_name='Очки за ничью')
    rounds_count = models.IntegerField(blank=True, null=True, verbose_name='Кол-во туров')

    # Round Robin & Leaderboard
    check_score_difference_on_draw = models.BooleanField(default=False, verbose_name='Если очки равны. Первым смотреть разницу в очках')
    
    # Round Robin
    mathces_count = models.IntegerField(blank=True, null=True, verbose_name='Количество игр с каждым игроком')

    def have_played(self, participant1, participant2):
        return Match.objects.filter(
            models.Q(participant1=participant1, participant2=participant2) |
            models.Q(participant1=participant2, participant2=participant1),
            stage__tournament=participant1.tournament
        ).exists()

    def is_full(self):
        return self.max_participants == self.participants.count()+1

    class Meta:
        verbose_name = 'Турнир'
        verbose_name_plural = 'Турниры'

    def __str__(self):
        return f"id: {self.id} Турнир: {self.name}"
    
    def delete(self, *args, **kwargs):
        self.stages.all().delete()
        self.participants.all().delete()
        super().delete(*args, **kwargs)


class TournamentStage(models.Model):
    start = models.DateTimeField(verbose_name='Начало этапа', blank=True, null=True,)
    end = models.DateTimeField(verbose_name='Окончание этапа', blank=True, null=True,)
    name = models.CharField(max_length=255, verbose_name='Название этапа')
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='stages', verbose_name='Турнир этапа')

    class Meta:
        verbose_name = 'Этап турнира'
        verbose_name_plural = 'Этапы турниров'

    def __str__(self):
        return f"Турнир {self.tournament}. {self.name}"


class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, blank=True, null=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='participants', verbose_name='Учатник турнира')
    
    # Swiss, Leaderboard
    score = models.FloatField(default=0.0, verbose_name="Общий счет")
    
    class Meta:
        verbose_name = 'Участник матча'
        verbose_name_plural = 'Участники матчей'

    def __str__(self):
        if self.user:
            return f"{self.tournament}. Участник {self.user}"
        else:
            return f"{self.tournament}. Команда {self.team}"


class StageResult(models.Model):
    stage = models.ForeignKey(TournamentStage, on_delete=models.CASCADE, related_name='results', verbose_name='Этап')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='stage_results', verbose_name='Участник')
    score = models.FloatField(default=0, verbose_name='Очки')

    class Meta:
        verbose_name = 'Результат этапа'
        verbose_name_plural = 'Результаты этапов'

    def __str__(self):
        return f"{self.participant} - {self.score} очков на этапе {self.stage.name}"


class Match(models.Model):
    scheduled_start = models.DateTimeField(verbose_name='Запланированное время начала', blank=True, null=True)
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое время начала')
    actual_end = models.DateTimeField(null=True, blank=True, verbose_name='Фактическое время окончания')    
    status = models.PositiveSmallIntegerField(choices=MATCH_STATUS, default=0, verbose_name='Статус')
    winner = models.ForeignKey(Participant, on_delete=models.SET_NULL, null=True, related_name='won_matches', verbose_name='Победитель')
    participant1 = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="match_participant1", blank=True, null=True, verbose_name="Участник 1")
    participant2 = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="match_participant2", blank=True, null=True, verbose_name="Участник 2")
    participant1_score = models.IntegerField(default=0, verbose_name='Счет участника 1')
    participant2_score = models.IntegerField(default=0, verbose_name='Счет участника 2')
    next_match = models.ForeignKey('Match', on_delete=models.CASCADE, related_name='next_match_on_win', blank=True, null=True, verbose_name="Следующий матч")
    next_lose_match = models.ForeignKey('Match', on_delete=models.CASCADE, related_name='next_match_on_lose', blank=True, null=True, verbose_name="Следующий матч при поражении")
    stage = models.ForeignKey(TournamentStage, on_delete=models.CASCADE, related_name='matches', verbose_name='Этап матча')
    
    class Meta:
        verbose_name = 'Матч'
        verbose_name_plural = 'Матчи'

    def __str__(self):
        return f"{self.stage}. Матч {self.id}"


class New(models.Model):
    text = models.TextField(verbose_name='Текст')
    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='news', verbose_name='Турнир')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Новость'
        verbose_name_plural = 'Новости'

    def __str__(self):
        return f"Новость {self.id}"


class TournamentPhoto(models.Model):
    match = models.ForeignKey(Tournament, related_name='photos', on_delete=models.CASCADE)
    photo = models.FileField(upload_to='tournament_photos/')
    
    class Meta:
        verbose_name = 'Фото турнира'
        verbose_name_plural = 'Фото турниров'

    def __str__(self):
        return f"Фото Турнира: {self.match}"