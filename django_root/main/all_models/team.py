from django.db import models
from main.all_models.sport import Sport
from main.models import User

# class TeamMemberRole(models.Model):
#     name = models.CharField(max_length=255, verbose_name='Название роли')

#     class Meta:
#         verbose_name = 'Роль в команде'
#         verbose_name_plural = 'Роли в командах'

#     def __str__(self):
#         return self.name

# class TeamMember(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
#     role = models.ForeignKey(TeamMemberRole, on_delete=models.CASCADE, verbose_name='Роль')

#     class Meta:
#         verbose_name = 'Член команды'
#         verbose_name_plural = 'Члены команд'

class Team(models.Model):
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, verbose_name='Вид спорта', blank=True, null=True)
    name = models.CharField(max_length=255, verbose_name='Название')
    logo = models.ImageField(upload_to='team_logos/', default='default_logo.jpg', verbose_name='Логотип')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    members = models.ManyToManyField(User, related_name='teams', verbose_name='Участники команды')
    
    class Meta:
        verbose_name = 'Команда'
        verbose_name_plural = 'Команды'

    def __str__(self):
        return self.name