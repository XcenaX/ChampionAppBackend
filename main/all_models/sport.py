from django.db import models

class Sport(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    image = models.ImageField(upload_to='sports_images/', verbose_name='Изображение')
    icon = models.ImageField(upload_to='sports_icons/', verbose_name='Иконка')

    class Meta:
        verbose_name = 'Вид спорта'
        verbose_name_plural = 'Виды спорта'

    def __str__(self):
        return self.name
