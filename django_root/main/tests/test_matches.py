from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from main.models import User
from main.all_models.match import AmateurMatch
from main.all_models.sport import Sport
import json

class AmateurMatchTests(APITestCase):
    def setUp(self):
        self.user1_data = {
            'email': 'test@mail.ru',
            'password': '123456',
            'confirm_password': '123456',
            'notify': True,
            'first_name': 'Test',
            'surname': 'User'
        }
        response = self.client.post(reverse('register'), json.dumps(self.user1_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(email=self.user1_data["email"])
        self.user1_data['id'] = user.id
        user.role = 3 # admin
        user.save()
        
        response = self.client.post(reverse('login'), json.dumps({'email': 'test@mail.ru', 'password': '123456'}), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1_token = response.data['access']
        
        self.user2_data = {
            'email': 'test2@mail.ru',
            'password': '123456',
            'confirm_password': '123456',
            'notify': True,
            'first_name': 'Test2',
            'surname': 'User2'
        }
        response = self.client.post(reverse('register'), json.dumps(self.user2_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user2_data['id'] = User.objects.get(email=self.user2_data["email"]).id

        response = self.client.post(reverse('login'), json.dumps({'email': 'test2@mail.ru', 'password': '123456'}), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user2_token = response.data['access']

        self.sport = Sport.objects.create(name='Football')        

    def test_create_match(self, auto_accept=True):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user1_token)
        url = '/api/amateur-matches/'
        test_image_base64 = 'data:image/png;base64,iVBO'
        data = {
            'name': 'Test Match',
            'description': 'A test match',
            'start': '2023-01-02T15:00:00Z',
            'address': '123 Test St',
            'city': 'Testville',
            'enter_price': 20,
            'sport': self.sport.id,
            'max_participants': 2,
            'auto_accept_participants': auto_accept,
            'lat': 34.05,
            'lon': -118.25,
            'photos_base64': [test_image_base64, test_image_base64]  # Отправляем два тестовых изображения
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AmateurMatch.objects.count(), 1)
        self.match = AmateurMatch.objects.first()

    def test_join_match(self, auto_accept=True):
        self.test_create_match(auto_accept)
        url = reverse('join_amateur_match')
        data = {'match': self.match.id}
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user2_token)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if auto_accept:
            self.assertTrue(self.match.participants.filter(id=self.user2_data['id']).exists())
        else:
            self.assertTrue(self.match.requests.filter(id=self.user2_data['id']).exists())

    def test_leave_match(self):
        self.test_join_match()  # Сначала присоединяем пользователя
        url = reverse('leave_amateur_match')
        data = {'match': self.match.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.match.participants.filter(id=self.user2_data['id']).exists())

    def test_accept_request(self):
        # есть запрос на вступление, который нужно одобрить  
        self.test_join_match(auto_accept=False)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user1_token)      
        url = reverse('accept_match_request')
        data = {'match': self.match.id, 'user': self.user2_data['id']}
        response = self.client.post(url, data, format='json')          
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.match.participants.filter(id=self.user2_data['id']).exists())
        self.assertFalse(self.match.requests.filter(id=self.user2_data['id']).exists())

    def test_decline_request(self):
        # есть запрос на вступление, который нужно отклонить
        self.test_join_match(auto_accept=False)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.user1_token)      
        url = reverse('refuse_match_request')
        data = {'match': self.match.id, 'user': self.user2_data['id']}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.match.requests.filter(id=self.user2_data['id']).exists())