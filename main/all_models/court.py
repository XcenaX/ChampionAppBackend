from django.db import models
from champion_backend.settings import EMAIL_HOST_USER
from main.models import User


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
