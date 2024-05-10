from turtle import position
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from main.all_models.tournament import Participant, Tournament, TournamentStage, Match
from main.models import User
from main.all_models.sport import Sport
import json
from main.services.tournament import print_tournament_bracket, print_next_matches_for_tournament

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
                        "test5@mail.ru", "test6@mail.ru", "test7@mail.ru", "test8@mail.ru",
                        "test9@mail.ru", "test10@mail.ru", "test11@mail.ru", "test12@mail.ru",]
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

    def create_tournament(self, bracket=0, auto_accept=True, tournament_type=0):
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
            'address': "ojfosjfosf",
            'bracket': bracket,
            "tournament_type": tournament_type,
            'prize_pool': 100000,
            "win_points": 3,
            "draw_points": 1,
            "rounds_count": 3,
            "mathces_count": 3,
            "group_stage_win_points": 3,
            "group_stage_draw_points": 1,
            "group_stage_rounds_count": 3,
            "mathces_count": 3,
            "final_stage_advance_count": 2,
            "participants_in_group": 4,
            'place': self.place,            
            'auto_accept_participants': auto_accept,
            'photos_base64': [test_image_base64, test_image_base64]  # Отправляем два тестовых изображения
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tournament.objects.count(), 1)
        self.tournament = Tournament.objects.first()

    def join_tournament(self, auto_accept=True, as_team=False):
        self.create_tournament(auto_accept=auto_accept)
        
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
        self.join_tournament()
        url = reverse('leave_tournament')
        data = {'tournament': self.tournament.id}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.tournament.participants.filter(user__id=self.users[1].id).exists())

    def test_accept_request(self):
        # есть запрос на вступление, который нужно одобрить  
        self.join_tournament(auto_accept=False)        

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
        self.join_tournament(auto_accept=False)   
        
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        url = reverse('refuse_tournament_request')
        data = {'tournament': self.tournament.id, 'user': self.users[1].id}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.tournament.users_requests.filter(id=self.users[1].id).exists())

    def add_participants(self, auto_accept=True, bracket=0, tournament_type=0):
        self.create_tournament(bracket=bracket, auto_accept=auto_accept, tournament_type=tournament_type)
        
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('add_tournament_participants', args=[self.tournament.id])
        participants_ids = [user.id for user in User.objects.all()]
        participants_count = len(participants_ids)
        data = {'participants': participants_ids}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if auto_accept:
            self.assertTrue(self.tournament.participants.count() == participants_count)
        else:
            self.assertTrue(self.tournament.users_requests.count() == participants_count)

    def create_bracket(self, auto_accept=True, bracket=0, tournament_type=0):
        self.add_participants(auto_accept, bracket=bracket, tournament_type=tournament_type)
        
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        matches = []
        
        participants_ids = [user.id for user in User.objects.all()]
        participants_ids_grouped = [participants_ids[i:i + 2] for i in range(0, len(participants_ids), 2)]
        for participants in participants_ids_grouped:
            matches.append({
                "participants": participants
            })  
        
        url = reverse('create_tournament_bracket', args=[self.tournament.id])
        data = {
            "matches": matches
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stages_count = TournamentStage.objects.filter(tournament=self.tournament).count()
        self.assertTrue(stages_count > 0)

    def update_matches(self, matches_data=[], results=[]):
        """
        results         -       for Leaderboard bracket
        matches_data    -       for other brackets 
        """

        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('update_tournament', args=[self.tournament.id])
        data = {
            'matches': matches_data,
            'results': results
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def end_stage(self):
        token = self.login_user(self.users[0].email)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)

        url = reverse('end_tournament_stage', args=[self.tournament.id])
        data = {}
        response = self.client.post(url, data, format='json')   
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def get_matches_data(self, stage):
        bracket = stage.tournament.bracket
        matches = Match.objects.filter(stage=stage)
        matches_data = []
        print(self.tournament.active_stage_position)
        if bracket in [0, 1, 2, 3]:
            for match in matches:
                matches_data.append({
                    'id': match.id,
                    'participant_1_score': 10,
                    'participant_2_score': 1
                })
        elif bracket == 4: # Leaderboard
            users = self.users
            if stage.tournament.tournament_type == 1:
                participants = Participant.objects.filter(tournament=stage.tournament, qualified=True)
                users = []
                for participant in participants:
                    if stage.tournament.is_team_tournament:
                        users.append(participant.team)
                    else:
                        users.append(participant.user)            
            users_len = len(users)        
            for score, user in enumerate(self.users, start=0):
                matches_data.append({
                    'participant_id': user.id,
                    'score': users_len - score
                })

        return matches_data

    # тесты для сеток турнира
    def test_single_elimination(self):
        print("\nTest single elimination...")
        current_bracket = 0
        self.create_bracket(auto_accept=True, bracket=current_bracket)
        
        # print_next_matches_for_tournament(self.tournament.id)
        # print([(stage.name, stage.position) for stage in TournamentStage.objects.filter(tournament=self.tournament)])
        
        stages_count = TournamentStage.objects.filter(tournament=self.tournament).count()
        count = 0
        has_next_stage = True
        while(has_next_stage):
            has_next_stage = self.tournament.has_next_stage()
            
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)
            
            self.update_matches(matches_data=matches_data)
            self.end_stage()
            
            self.tournament = Tournament.objects.get(id=self.tournament.id)            
            
            # print_tournament_bracket(self.tournament.id)
            
            count += 1
            if count == stages_count+1:
                raise Exception("Something wrong with ending stages in Single elimination")
        
        places = self.tournament.get_places()
        predicted_places = ["test3@mail.ru", "test7@mail.ru", "test5@mail.ru", "test9@mail.ru", "test@mail.ru", "test4@mail.ru", "test6@mail.ru", "test8@mail.ru", "test2@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_double_elimination(self):
        print("\nTest double elimination...")
        current_bracket = 1
        self.create_bracket(auto_accept=True, bracket=current_bracket)
        self.tournament = Tournament.objects.get(id=self.tournament.id)
        
        # print_next_matches_for_tournament(self.tournament.id)
        # print([(stage.name, stage.position) for stage in TournamentStage.objects.filter(tournament=self.tournament)])
        
        stages_count = TournamentStage.objects.filter(tournament=self.tournament).count()
        count = 0
        has_next_stage = True
        while(has_next_stage):
            has_next_stage = self.tournament.has_next_stage()
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            
            # print_tournament_bracket(self.tournament.id)

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id)

            
            count += 1
            if count == stages_count+1:
                raise Exception("Something wrong with ending stages in Double elimination")
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test5@mail.ru", "test2@mail.ru", "test6@mail.ru", "test3@mail.ru", "test7@mail.ru", "test4@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        # for i in range(places_count):
        #     self.assertEqual(predicted_places[i], places[i].user.email)

    def test_round_robin(self):
        print("\nTest Round Robin...")
        current_bracket = 2
        self.create_bracket(auto_accept=True, bracket=current_bracket)
        stages_count = TournamentStage.objects.filter(tournament=self.tournament).count()
        count = 0
        has_next_stage = True
        while(has_next_stage):
            has_next_stage = self.tournament.has_next_stage()
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            
            self.tournament = Tournament.objects.get(id=self.tournament.id)            
            
            count += 1
            if count == stages_count+1:
                raise Exception("Something wrong with ending stages in Round Robin")
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test3@mail.ru", "test4@mail.ru", "test5@mail.ru", "test6@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_swiss(self):
        print("\nTest Swiss...")
        current_bracket = 3
        self.create_bracket(auto_accept=True, bracket=current_bracket)
        
        has_next_stage = True
        while(has_next_stage):
            has_next_stage = self.tournament.active_stage_position < self.tournament.rounds_count                       
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id) 
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test3@mail.ru", "test4@mail.ru", "test5@mail.ru", "test6@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_leaderboard(self):
        print("\nTest Leaderboard...")
        current_bracket = 4
        self.create_bracket(auto_accept=True, bracket=current_bracket)
        
        has_next_stage = True
        while(has_next_stage):
            has_next_stage = self.tournament.active_stage_position < self.tournament.rounds_count                       
            active_stage = self.tournament.get_active_stage()
            results = self.get_matches_data(active_stage)            

            self.update_matches(results=results)
            self.end_stage()
            
            self.tournament = Tournament.objects.get(id=self.tournament.id) 
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test3@mail.ru", "test4@mail.ru", "test5@mail.ru", "test6@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    # тесты для сеток Двуступенчатого турнира
    def test_grand_tournament_single(self):
        print("\nTest Grand Tournament with Single elimination...")
        current_bracket = 0
        self.create_bracket(auto_accept=True, bracket=current_bracket, tournament_type=1)        

        has_next_stage = True
        while(has_next_stage):
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id) 

            #print_tournament_bracket(self.tournament.id)

            has_next_stage = self.tournament.has_next_stage(active_stage)
        
        #print_next_matches_for_tournament(self.tournament.id)
        #print([(stage.name, stage.position) for stage in TournamentStage.objects.filter(tournament=self.tournament)])
        
        places = self.tournament.get_places()
        predicted_places = ["test6@mail.ru", "test2@mail.ru", "test@mail.ru", "test5@mail.ru", "test3@mail.ru", "test4@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        #print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_grand_tournament_double(self):
        print("\nTest Grand Tournament with Double elimination...")
        current_bracket = 1
        self.create_bracket(auto_accept=True, bracket=current_bracket, tournament_type=1)
        
        has_next_stage = True
        while(has_next_stage):
            # print_tournament_bracket(self.tournament.id)
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id)            
            has_next_stage = self.tournament.has_next_stage(active_stage)    
        
        #print_next_matches_for_tournament(self.tournament.id)
        #print([(stage.name, stage.position) for stage in TournamentStage.objects.filter(tournament=self.tournament)])

        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test5@mail.ru", "test3@mail.ru", "test6@mail.ru", "test4@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        #print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_grand_tournament_round_robin(self):
        print("\nTest Grand Tournament with Round Robin...")
        current_bracket = 2
        self.create_bracket(auto_accept=True, bracket=current_bracket, tournament_type=1)
        
        has_next_stage = True
        while(has_next_stage):
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id) 
                       
            has_next_stage = self.tournament.has_next_stage(active_stage)
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test5@mail.ru", "test6@mail.ru", "test3@mail.ru", "test4@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_grand_tournament_swiss(self):
        print("\nTest Grand Tournament with Swiss...")
        current_bracket = 3
        self.create_bracket(auto_accept=True, bracket=current_bracket, tournament_type=1)
        
        has_next_stage = True
        while(has_next_stage):
            active_stage = self.tournament.get_active_stage()
            matches_data = self.get_matches_data(active_stage)            

            self.update_matches(matches_data=matches_data)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id) 
                       
            has_next_stage = self.tournament.has_next_stage(active_stage)
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test5@mail.ru", "test6@mail.ru", "test3@mail.ru", "test4@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)

    def test_grand_tournament_leaderboard(self):
        print("\nTest Grand Tournament with Leaderboard...")
        current_bracket = 4
        self.create_bracket(auto_accept=True, bracket=current_bracket, tournament_type=1)
        
        has_next_stage = True
        while(has_next_stage):
            active_stage = self.tournament.get_active_stage()
            results = self.get_matches_data(active_stage)            

            self.update_matches(results=results)
            self.end_stage()
            self.tournament = Tournament.objects.get(id=self.tournament.id) 
                       
            has_next_stage = self.tournament.has_next_stage(active_stage)
        
        places = self.tournament.get_places()
        predicted_places = ["test@mail.ru", "test2@mail.ru", "test5@mail.ru", "test6@mail.ru", "test3@mail.ru", "test4@mail.ru", "test7@mail.ru", "test8@mail.ru",]
        places_count = len(places)        
        # print([(participant.place, participant.user.email) for participant in places])
        for i in range(places_count):
            self.assertEqual(predicted_places[i], places[i].user.email)
