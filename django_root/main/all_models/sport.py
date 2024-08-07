from django.db import models

class Sport(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    image = models.FileField(upload_to='sports_images/', verbose_name='Изображение')
    icon = models.FileField(upload_to='sports_icons/', verbose_name='Иконка', blank=True, null=True)

    class Meta:
        verbose_name = 'Вид спорта'
        verbose_name_plural = 'Виды спорта'

    def __str__(self):
        return self.name
