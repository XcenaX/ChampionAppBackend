from django.db import models
from main.all_models.sport import Sport
from main.models import User


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
