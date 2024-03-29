from django.db import models
from main.models import User


class Plan(models.Model):
    name = models.CharField(
        max_length=255, verbose_name='Наименование')
    price_month = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name='Цена (в месяц)')
    price_half_year = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name='Цена (в полгода)')
    price_year = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00, verbose_name='Цена (в год)')

    class Meta:
        verbose_name = 'План подписки'
        verbose_name_plural = 'Планы подписок'

    def __str__(self):
        return self.name
    

class Subscription(models.Model):    
    plan = models.ForeignKey(
        Plan,
        on_delete=models.RESTRICT,
        related_name='subscriptions',
        verbose_name='План'
    )
    is_monthly = models.BooleanField(
        null=False,
        default=True,
        verbose_name='Ежемесечная подписка'
    )    
    start_date = models.DateTimeField(verbose_name='Начало действия')
    end_date = models.DateTimeField(verbose_name='Конец действия')
    is_auto_renew = models.BooleanField(
        default=True, verbose_name='Автопродление')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return str(self.id)


class Transaction(models.Model):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.RESTRICT,
        related_name='transaction',
        verbose_name='Подписка',
        null=True
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name='Сумма')
    type = models.PositiveSmallIntegerField(verbose_name='Тип')
    date_time = models.DateTimeField(verbose_name='Дата совершения')
    is_paid = models.BooleanField(default=False, verbose_name='Завершена')

    class Meta:
        verbose_name = 'Транзакция'
        verbose_name_plural = 'Транзакции'

    def __str__(self):
        if self.user:
            return f'{self.user.id} - {self.date_time}'
        return f'Транзакция от {self.date_time}'