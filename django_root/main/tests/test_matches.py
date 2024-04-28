from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from main.models import User
from main.all_models.match import AmateurMatch
from main.all_models.sport import Sport
import json

class AmateurMatchTests(APITestCase):
    def register_user(self, email, role=0):
        user_data = {
            'email': email,
            'password': '123456',
            'confirm_password': '123456',
            'notify': True,
            'first_name': 'Test',
            'surname': 'User'
        }
        response = self.client.post(reverse('register'), json.dumps(user_data), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(email=user_data["email"])
        if role != 0:
            user.role = role
            user.save()

        self.users.append(user)
    
    def login_user(self, email):
        response = self.client.post(reverse('login'), json.dumps({'email': email, 'password': '123456'}), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data['access']

    def setUp(self):
        self.users = []
        participants = ["test@mail.ru", "test2@mail.ru"]
        count = 0
        for participant in participants:
            if count == 0:
                self.register_user(participant, role=3)
                count = 1
            else:
                self.register_user(participant)

        self.sport = Sport.objects.create(name='Футбол')        

    def test_create_match(self, auto_accept=True):
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
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

        token = self.login_user(self.users[1].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('join_amateur_match')
        data = {'match': self.match.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if auto_accept:
            self.assertTrue(self.match.participants.filter(id=self.users[1].id).exists())
        else:
            self.assertTrue(self.match.requests.filter(id=self.users[1].id).exists())

    def test_leave_match(self):
        self.test_join_match()  # Сначала присоединяем пользователя
        url = reverse('leave_amateur_match')
        data = {'match': self.match.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.match.participants.filter(id=self.users[1].id).exists())

    def test_accept_request(self):
        # есть запрос на вступление, который нужно одобрить  
        self.test_join_match(auto_accept=False) 

        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('accept_match_request')
        data = {'match': self.match.id, 'user': self.users[1].id}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.match.participants.filter(id=self.users[1].id).exists())
        self.assertFalse(self.match.requests.filter(id=self.users[1].id).exists())

    def test_decline_request(self):
        # есть запрос на вступление, который нужно отклонить
        self.test_join_match(auto_accept=False)    

        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('refuse_match_request')
        data = {'match': self.match.id, 'user': self.users[1].id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.match.requests.filter(id=self.users[1].id).exists())