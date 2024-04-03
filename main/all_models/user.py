import random
import string
from django.db import models
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from traitlets import default
from champion_backend.settings import EMAIL_HOST_USER
from django.contrib import admin


class Confirmation(models.Model):
    email = models.CharField(max_length=100, default='')
    email_type = models.CharField(max_length=2, default="0")
    code = models.CharField(max_length=6, default='')

    EMAIL_TYPES = {
        "0": {
            "theme": "Подтверждение почты",
            "message": "confirm_code.html"
        },
        "1": {
            "theme": "Восстановление пароля",
            "message": "reset_password.html"
        },
    }

    def save(self, *args, **kwargs):
        """Генерируем код"""
        if not self.code:
            for confirmation in Confirmation.objects.filter(email=self.email):
                confirmation.delete()

            letters = string.digits
            code_length = 6
            random_str = ''.join(random.choice(letters) for i in range(code_length))
            self.code = random_str

            email_info = self.EMAIL_TYPES[self.email_type]

            try:
                html_message = render_to_string(email_info["message"], {'code': random_str})
                plain_message = strip_tags(html_message)
                send_mail(
                    email_info["theme"],
                    plain_message,
                    EMAIL_HOST_USER,
                    [self.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                # email = EmailMessage('Подтверждение почты', "Для подтверждения вашей почты введите этот код: <h2>{0}</h2>".format(random_str), to=[self.email])
                # email.send()
            except Exception as e:
                print("ОШИБКА ПРИ ОТПРАВКЕ EMAIL: ", e)

        super().save(*args, **kwargs)
    
    @admin.display(description='Почта')
    def email_display(self):
        return self.email
    
    @admin.display(description='Код подтверждения')
    def code_display(self):
        return self.code
    

