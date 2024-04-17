from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.urls import reverse

from main.all_models.match import AmateurMatch

class AmateurMatchTestCase(APITestCase):

    def setUp(self):
        # Создание пользователей
        self.user1 = User.objects.create_user(email='user1@mail.ru', password='pass1')
        self.user2 = User.objects.create_user(email='user2@mail.ru', password='pass2')
        
        # Создание токенов для аутентификации
        self.token1 = Token.objects.create(user=self.user1)
        self.token2 = Token.objects.create(user=self.user2)
        
        # Создание матча
        self.match = AmateurMatch.objects.create(name="Match 1", owner=self.user1, enter_price=100)
        
    def test_amateur_match_workflow(self):
        # Вход пользователя 1 и создание матча
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.post(reverse('amateurmatch-list'), {
            'name': 'New Match',
            'enter_price': 50
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Вход пользователя 2 и подача заявки на матч
        match_id = response.data['id']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token2.key)
        response = self.client.post(reverse('amateurmatch-apply', kwargs={'pk': match_id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Пользователь 1 принимает заявку
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token1.key)
        response = self.client.post(reverse('amateurmatch-accept', kwargs={'pk': match_id, 'user_id': self.user2.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Изменение матча пользователем 1
        response = self.client.patch(reverse('amateurmatch-detail', kwargs={'pk': match_id}), {
            'enter_price': 75
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Удаление пользователя 2 из участников матча
        response = self.client.delete(reverse('amateurmatch-remove-participant', kwargs={'pk': match_id, 'user_id': self.user2.id}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def tearDown(self):
        # Очистка данных после каждого теста
        self.user1.delete()
        self.user2.delete()
        AmateurMatch.objects.all().delete()
