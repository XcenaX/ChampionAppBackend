from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from main.all_models.tournament import Tournament
from main.models import User
from main.all_models.sport import Sport
import json

class TournamentsTests(APITestCase):
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
        participants = ["test@mail.ru", "test2@mail.ru", "test3@mail.ru", "test4@mail.ru",
                        "test5@mail.ru", "test6@mail.ru", "test7@mail.ru", "test8@mail.ru"]
        count = 0
        for participant in participants:
            if count == 0:
                self.register_user(participant, role=3)
                count = 1
            else:
                self.register_user(participant)

        self.sport = Sport.objects.create(name='Футбол')
        self.place = 'Футбольное поле'
        self.tournament = None        

    def test_create_tournament(self, bracket=0, auto_accept=True):
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        
        url = '/api/tournaments/'
        test_image_base64 = 'data:image/png;base64,iVBO'
        data = {
            'name': 'Test Tournament',
            'description': 'A test tornament',
            'start': '2023-01-02T15:00:00Z',
            'end': '2023-04-02T15:00:00Z',
            'enter_price': 1500,
            'sport': self.sport.id,
            'max_participants': 8,
            'city': "Астана",
            'bracket': bracket,
            'prize_pool': 100000,
            'place': self.place,            
            'auto_accept_participants': auto_accept,
            'photos_base64': [test_image_base64, test_image_base64]  # Отправляем два тестовых изображения
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tournament.objects.count(), 1)
        self.tournament = Tournament.objects.first()

    def test_join_tournament(self, auto_accept=True, as_team=False):
        self.test_create_tournament(auto_accept=auto_accept)
        
        token = self.login_user(self.users[1].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('join_tournament')
        data = {'tournament': self.tournament.id}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if auto_accept:
            self.assertTrue(self.tournament.participants.filter(user__id=self.users[1].id).exists())
        else:
            self.assertTrue(self.tournament.users_requests.filter(id=self.users[1].id).exists())

    def test_leave_tournament(self):
        self.test_join_tournament()
        url = reverse('leave_tournament')
        data = {'tournament': self.tournament.id}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.tournament.participants.filter(user__id=self.users[1].id).exists())

    def test_accept_request(self):
        # есть запрос на вступление, который нужно одобрить  
        self.test_join_tournament(auto_accept=False)        

        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('accept_tournament_request')
        data = {'tournament': self.tournament.id, 'user': self.users[1].id}
        response = self.client.post(url, data, format='json')          
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.tournament.participants.filter(user__id=self.users[1].id).exists())
        self.assertFalse(self.tournament.users_requests.filter(id=self.users[1].id).exists())

    def test_decline_request(self):
        # есть запрос на вступление, который нужно отклонить
        self.test_join_tournament(auto_accept=False)   
        
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('refuse_tournament_request')
        data = {'tournament': self.tournament.id, 'user': self.users[1].id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.tournament.users_requests.filter(id=self.users[1].id).exists())