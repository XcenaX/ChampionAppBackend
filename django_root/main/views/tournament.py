from main.all_models.tournament import Match, Participant, StageResult, Tournament, Team, TournamentStage

from champion_backend.settings import EMAIL_HOST_USER
from main.models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.response import Response

from rest_framework import viewsets, status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from main.filters import TournamentFilter

from rest_framework.views import APIView

from django.core.mail import send_mail

from main.serializers.tournament import TournamentListSerializer, TournamentSerializer

import json
import random
from django.db.models import Q

from django.shortcuts import get_object_or_404

from main.services.img_functions import _decode_photo

from django.db.models import Min, Max
from rest_framework import serializers
from django.db.models import Count

class TournamentViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TournamentFilter
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch']
    queryset = Tournament.objects.select_related('sport', 'owner').annotate(participants_count=Count('participants'))
    # serializer_class = TournamentSerializer

    def __init__(self, *args, **kwargs):
        super(TournamentViewSet, self).__init__(*args, **kwargs)
        self.serializer_action_classes = {
            'list': TournamentListSerializer,
            'create': TournamentSerializer,
            'retrieve': TournamentSerializer,
            'update': TournamentSerializer,
            'partial_update': TournamentSerializer,
            'destroy': TournamentSerializer,
        }
    
    def get_serializer_class(self, *args, **kwargs):
        kwargs['partial'] = True
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super(TournamentViewSet, self).get_serializer_class()

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'rules': openapi.Schema(type=openapi.TYPE_STRING),                
                'prize_pool': openapi.Schema(type=openapi.TYPE_INTEGER, description='Призовой фонд'),                
                
                'start': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Дата и время начала в формате YYYY-MM-DDTHH:MM:SSZ',
                    example='2023-01-01T15:00:00Z'
                ),
                'enter_price': openapi.Schema(type=openapi.TYPE_INTEGER, description='Ставка'),
                'sport': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID спорта'),
                'max_participants': openapi.Schema(type=openapi.TYPE_INTEGER, description='Макс кол-во участников'),
                'photo_base64': openapi.Schema(type=openapi.TYPE_STRING, description='Фото матча в формате base64'),
                'auto_accept_participants': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Автоматически принимать всех участников'),
                'is_team_tournament': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='Командный турнир'),
                'bracket': openapi.Schema(type=openapi.TYPE_INTEGER, description='Тип сетки'),
            },
            required=['name', 'start', 'enter_price', 'sport', 'max_participants']
        )
    )
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.send_email_to_participants(instance)

    def send_email_to_participants(self, tournament):
        participants = tournament.participants.all()        
        recipient_list = [participant.email for participant in participants if participant.email]
        
        if recipient_list:            
            send_mail(
                'ChampionApp. Турнир "{tournament.name}" был обновлен. Пожалуйста, проверьте детали.',
                "",
                EMAIL_HOST_USER,
                recipient_list,
                fail_silently=False,
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class UpdateTournament(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Обновить матчи турнира',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'matches': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='Список матчей для обновления',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID матча'),
                            'scheduled_start': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Запланированное время начала матча'),
                            'actual_start': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Фактическое время начала матча'),
                            'actual_end': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Фактическое время окончания матча'),                            
                            'participant_1_score': openapi.Schema(type=openapi.TYPE_INTEGER, description='Счет первого участника'),
                            'participant_2_score': openapi.Schema(type=openapi.TYPE_INTEGER, description='Счет второго участника'),
                        },
                        required=['id']
                    ),
                ),
                "results": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='Обновить счет участников на определенном событии(туре) турнира (Leaderboard)',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'participant_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID участника'),
                            'score': openapi.Schema(type=openapi.TYPE_INTEGER, description='Счет участника'),
                        },
                        required=['id']
                    ),
                ),
                "stage": openapi.Schema(type=openapi.TYPE_INTEGER, description='id Этапа')
            }
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Турнир обновлен!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def patch(self, request, id):
        try:
            tournament = get_object_or_404(Tournament, id=id, owner=request.user)
            data = json.loads(request.body)
            matches_data = data.get("matches", [])
            results_data = data.get("results", [])
            stage_id = data.get("stage", None)

            if results_data and stage_id:
                stage = TournamentStage.objects.get(id=stage_id)                
                for result_data in results_data:
                    participant_id = result_data.get("participant_id", None)
                    if not participant_id:
                        return Response({'success': False, 'message': 'Ошибка при обновлении: Участник с переданым participant_id не найден!'}, status=status.HTTP_400_BAD_REQUEST)

                    participant = Participant.objects.get((Q(user__id=participant_id) | Q(team__id=participant_id)) & Q(tournament=stage.tournament))
                    score = result_data.get("score", 0)
                    try:
                        result = StageResult.objects.get(stage=stage, participant=participant)
                        result.score = score
                        result.save()
                    except:
                        result = StageResult.objects.create(stage=stage, participant=participant, score=score)

            for match_data in matches_data:
                match = get_object_or_404(Match, pk=match_data.get("id"))
                
                match.scheduled_start = match_data.get("scheduled_start", match.scheduled_start)
                match.actual_start = match_data.get("actual_start", match.actual_start)
                match.actual_end = match_data.get("actual_end", match.actual_end)
                
                if "participant_1_score" in match_data and "participant_2_score" in match_data:
                    participant_1_score = match_data.get("participant_1_score")
                    participant_2_score = match_data.get("participant_2_score")                                        

                    if match.status == 2: # Если матч уже был завершен но нужно поменять результаты
                        if (match.participant1_score < match.participant2_score) != (participant_1_score < participant_2_score): # Если результат матча изменился
                            if(participant_1_score < participant_2_score):
                                match.participant1.score -= tournament.win_points
                                match.participant2.score += tournament.win_points
                            elif(participant_1_score > participant_2_score):
                                match.participant1.score += tournament.win_points
                                match.participant2.score -= tournament.win_points
                            else:
                                if match.participant1_score < match.participant2_score:
                                    match.participant2 -= tournament.win_points + tournament.draw_points
                                    match.participant1 += tournament.draw_points
                                elif match.participant1_score > match.participant2_score:
                                    match.participant1 -= tournament.win_points + tournament.draw_points
                                    match.participant2 += tournament.draw_points                                                         
                    else:
                        winner = None
                        loser = None

                        if participant_1_score > participant_2_score:
                            winner = match.participant1
                            loser = match.participant2
                        elif participant_1_score < participant_2_score:
                            winner = match.participant2
                            loser = match.participant1                                          
                                        
                        if not winner and loser:
                            match.participant1.score += tournament.draw_points
                            match.participant2.score += tournament.draw_points
                        else:
                            winner.score += tournament.win_points                        

                    match.participant1_score = participant_1_score
                    match.participant2_score = participant_2_score
                    match.winner = winner
                    match.status = 2
                    match.save()
                    match.participant1.save()
                    match.participant2.save()
                    
            if tournament.bracket == 0: # single
                if match.next_match:
                    if not match.next_match.participant1:
                        match.next_match.participant1 = winner
                    elif not match.next_match.participant2:
                        match.next_match.participant2 = winner
                    match.next_match.save()
            if tournament.bracket == 1: # double
                if match.next_match:
                    if not match.next_match.participant1:
                        match.next_match.participant1 = winner
                    elif not match.next_match.participant2:
                        match.next_match.participant2 = winner
                    match.next_match.save()

                if match.next_lose_match:
                    if not match.next_lose_match.participant1:
                        match.next_lose_match.participant1 = loser
                    elif not match.next_lose_match.participant2:
                        match.next_lose_match.participant2 = loser
                    match.next_lose_match.save()
            elif tournament.bracket == 2: # round
                pass # Новые матчи создавать не нужно (пока что)
            elif tournament.bracket == 3 or tournament.bracket == 4 and tournament.stages.count() != tournament.rounds_count: # swiss
                last_stage = tournament.stages.last()
                print(last_stage)
                if last_stage:
                    # Проверяем, завершены ли все матчи последнего этапа
                    if all(match.status == 2 for match in last_stage.matches.all()):                        
                        if tournament.stages.count() < tournament.rounds_count:
                            new_stage = TournamentStage.objects.create(
                                name=f"Этап {tournament.stages.count() + 1}",                                        
                            )
                            
                            self.create_new_swiss_round(new_stage, tournament)

                            tournament.stages.add(new_stage)                

            return Response({'success': True, 'message': 'Турнир обновлен!'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'success': False, 'message': f'Ошибка при обновлении: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
    def create_new_swiss_round(self, stage, tournament):
        participants = list(tournament.participants.all())
        # Сортировка участников по их текущему счету в убывающем порядке
        participants.sort(key=lambda x: x.score, reverse=True)
        print(participants)

        # Организация пар на основе текущих результатов
        # Используем жадный метод для создания пар, чтобы максимально сбалансировать уровень соперников
        used = set()
        pairs = []

        for participant in participants:
            if participant not in used:
                best_match = None
                # Ищем наиболее подходящего соперника, не игравшего с данным участником
                for potential_opponent in participants:
                    if potential_opponent not in used and potential_opponent != participant and not tournament.have_played(participant, potential_opponent):
                        best_match = potential_opponent
                        break
                if best_match:
                    pairs.append((participant, best_match))
                    used.add(participant)
                    used.add(best_match)

        # Создаем матчи на основе сформированных пар
        for participant1, participant2 in pairs:
            match = Match.objects.create(
                participant1=participant1,
                participant2=participant2,                
            )
            stage.matches.add(match)


class JoinTournament(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Присоединится к турниру',        
        request_body = openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament', 'is_team'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="ID турнира"),
                'is_team': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Присоединиться как команда"),
                'team': openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'name': openapi.Schema(type=openapi.TYPE_STRING, description="Имя команды"),
                        'logo': openapi.Schema(type=openapi.TYPE_STRING, description="Логотип команды в формате Base64 (необязательно)", nullable=True),
                        'members': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_INTEGER),
                            description="Массив ID участников команды"
                        )
                    },
                    description="Информация о команде"
                )
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Вы успешно присоединились к матчу!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]
            is_team = data.get("is_team", False)
            team = data.get("team", None)
            team_name = ""
            if team:
                team_name = team.get("name", "")
                team_logo = team.get("logo", "")
                team_members = team.get("members", [])
                if not team_members:
                    return Response({'success': False, 'message': 'Команда не может быть пустой!'}, status=status.HTTP_400_BAD_REQUEST)

            tournament = Tournament.objects.get(id=tournament_id)
            
            if not tournament.is_full():
                new_team = None
                if is_team:
                    if tournament.participants.filter(team__name=team_name):
                        return Response({'success': False, 'message': 'Вы уже присоеденились к турниру!'}, status=status.HTTP_400_BAD_REQUEST)
                    new_team = Team.objects.create(name=team_name)
                    if team_logo:
                        new_team.logo = _decode_photo(team_logo)
                    if team_members:
                        for user_id in team_members:
                            try:
                                user = User.objects.get(id=user_id)
                                new_team.members.add(user)
                            except:
                                pass
                if tournament.auto_accept_participants:
                    if not is_team:
                        if tournament.participants.filter(user=request.user).exists():
                            return Response({'success': False, 'message': 'Вы уже присоеденились к турниру!'}, status=status.HTTP_400_BAD_REQUEST)
                        new_participant = Participant.objects.create(user=request.user)                        
                    else:                        
                        new_participant = Participant.objects.create(team=new_team)

                    tournament.participants.add(new_participant)
                    
                    return Response({'success': True, 'message': 'Вы успешно присоединились к матчу!'}, status=200)
                else:
                    if is_team:
                        if tournament.teams_requests.contains(new_team):
                            return Response({'success': False, 'message': 'Вы уже подали заявку на этот матч!'}, status=status.HTTP_400_BAD_REQUEST)                
                        tournament.teams_requests.add(new_team)
                    else:
                        if tournament.users_requests.contains(request.user):
                            return Response({'success': False, 'message': 'Вы уже подали заявку на этот матч!'}, status=status.HTTP_400_BAD_REQUEST)
                        tournament.users_requests.add(request.user)
                    
                    return Response({'success': True, 'message': 'Вы успешно подали заявку на турнир!'}, status=200)
            else:
                return Response({'success': False, 'message': 'Мест на турнир уже нет!'}, status=status.HTTP_400_BAD_REQUEST) 

            # TODO
            # сделать уведомление создателя турнира, что на него откликнулись
        except Exception as error:
            return Response({'success': False, 'message': error}, status=status.HTTP_401_UNAUTHORIZED) 


class LeaveTournament(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Покинуть турнир',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id турнира"),     
                'team': openapi.Schema(type=openapi.TYPE_INTEGER, description="id команды")
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Вы успешно покинули турнир!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]
            team_id = data.get("team", None)            
            tournament = Tournament.objects.get(id=tournament_id)
            if team_id:
                if tournament.participants.filter(team__id=team_id).exists():
                    team = Team.objects.get(id=team_id)     
                    participants = Participant.objects.filter(team=team, participants_tournament=tournament)   
                    for participant in participants:
                        tournament.participants.remove(participant)        
                    return Response({'success': True, 'message': 'Вы покинули турнир!'}, status=status.HTTP_200_OK)
                else:
                    return Response({'success': False, 'message': 'Участник не состоит в этом матче но пытается выйти из него!'}, status=status.HTTP_400_BAD_REQUEST)         
            else:
                if tournament.participants.filter(user=request.user).exists():
                    participants = Participant.objects.filter(user=request.user, participants_tournament=tournament)   
                    for participant in participants:
                        tournament.participants.remove(participant)        
                    return Response({'success': True, 'message': 'Вы покинули турнир!'}, status=status.HTTP_200_OK)
                else:
                    return Response({'success': False, 'message': 'Участник не состоит в этом матче но пытается выйти из него!'}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({'success': False, 'message': 'Турнира с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class AcceptTournamentRequest(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Принять заявку человека/команды на турнир',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id турнира"),                
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="id пользователя"),                
                'team': openapi.Schema(type=openapi.TYPE_INTEGER, description="id команды"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Пользователь был принят!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]
            user_id = data.get("user", None)
            team_id = data.get("team", None)

            tournament = Tournament.objects.get(id=tournament_id)
            
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    
                    if not tournament.users_requests.contains(user):
                        return Response({'success': False, 'message': 'Переданного пользователя нет в списке заявок!'}, status=status.HTTP_400_BAD_REQUEST) 
                    if tournament.participants.filter(user=user).exists():
                        return Response({'success': False, 'message': 'Переданный пользователь уже участвует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 

                    tournament.users_requests.remove(user)
                    new_participant = Participant.objects.create(user=user)
                    tournament.participants.add(new_participant)
                except:
                    return Response({'success': False, 'message': 'Пользователь с переданным user id не найден!'}, status=status.HTTP_400_BAD_REQUEST)             
            elif team_id:
                try:
                    team = Team.objects.get(id=team_id)
                    
                    if not tournament.teams_requests.contains(team):
                        return Response({'success': False, 'message': 'Переданной команды нет в списке заявок!'}, status=status.HTTP_400_BAD_REQUEST) 
                    if tournament.participants.filter(team=team).exists():
                        return Response({'success': False, 'message': 'Переданная команда уже участвует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 
                    
                    tournament.teams_requests.remove(team)
                    new_participant = Participant.objects.create(team=team)
                    tournament.participants.add(new_participant)
                except:
                    return Response({'success': False, 'message': 'Команда с переданным team id не найдена!'}, status=status.HTTP_400_BAD_REQUEST) 

            return Response({'success': True, 'message': 'Пользователь принят на матч!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Турнира или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class RefuseTournamentRequest(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Отклонить заявку человека/команды на турнир',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="id пользователя"),                
                'team': openapi.Schema(type=openapi.TYPE_INTEGER, description="id команды"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Пользователь был отклонен!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]
            user_id = data.get("user", None)
            team_id = data.get("team", None)

            tournament = Tournament.objects.get(id=tournament_id)
            
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    if not tournament.users_requests.contains(user):
                        return Response({'success': False, 'message': 'Переданного пользователя нет в списке заявок!'}, status=status.HTTP_400_BAD_REQUEST) 
                    tournament.users_requests.remove(user)
                except:
                    return Response({'success': False, 'message': 'Пользователя с переданным user id не существует!'}, status=status.HTTP_400_BAD_REQUEST)                     
            elif team_id:
                try:
                    team = Team.objects.get(id=team_id)
                    if not tournament.teams_requests.contains(team):
                        return Response({'success': False, 'message': 'Переданной команды нет в списке заявок!'}, status=status.HTTP_400_BAD_REQUEST) 
                    tournament.teams_requests.remove(team)
                except:
                    return Response({'success': False, 'message': 'Команды с переданным team id не существует!'}, status=status.HTTP_400_BAD_REQUEST)             

            return Response({'success': True, 'message': 'Пользователь был отклонен!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Турнира или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class DeleteTournamentParticipants(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Удалить участников из турнира',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id турнира"),                
                'users': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id пользователей"),                
                'teams': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id команд"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Пользователь был удален!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]
            users_id = data.get("users", None)
            teams_id = data.get("teams", None)

            tournament = Tournament.objects.get(id=tournament_id)
            participant = None

            if users_id:
                for user_id in users_id:
                    try:
                        user = User.objects.get(id=user_id)
                        participant = tournament.participants.filter(user=user).first()
                        if not participant:
                            return Response({'success': False, 'message': 'Переданного пользователя нет в списке участников!'}, status=status.HTTP_400_BAD_REQUEST)         
                        tournament.users_requests.remove(user)                    
                    except:
                        return Response({'success': False, 'message': 'Пользователя с переданным user id не существует!'}, status=status.HTTP_400_BAD_REQUEST)                     
                    tournament.participants.remove(participant)
            elif teams_id:
                for team_id in teams_id:                
                    try:
                        team = Team.objects.get(id=team_id)
                        participant = tournament.participants.filter(team=team).first()
                        if not participant:
                            return Response({'success': False, 'message': 'Переданного пользователя нет в списке участников!'}, status=status.HTTP_400_BAD_REQUEST)         
                        tournament.teams_requests.remove(team)
                    except:
                        return Response({'success': False, 'message': 'Команды с переданным team id не существует!'}, status=status.HTTP_400_BAD_REQUEST)             

                    tournament.participants.remove(participant)
            
            return Response({'success': True, 'message': 'Пользователь был удален!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Турнира или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class AddTournamentParticipants(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Добавить участников на турнир',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
                'users': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id пользователей"),                
                'teams': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id команд"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Пользователь был принят!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            
            tournament_id = data["tournament"]
            users_id = data.get("users", [])
            teams_id = data.get("teams", [])

            tournament = Tournament.objects.get(id=tournament_id)

            if users_id:
                for user_id in users_id:
                    try:
                        user = User.objects.get(id=user_id)                    
                        if tournament.participants.filter(user=user).exists():
                            return Response({'success': False, 'message': 'Переданный пользователь уже учавствует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 
                        if tournament.users_requests.contains(user):
                            tournament.users_requests.remove(user)
                        new_participant = Participant.objects.create(user=user)
                        tournament.participants.add(new_participant)
                    except:
                        return Response({'success': False, 'message': 'Пользователя с переданным user id не существует!'}, status=status.HTTP_400_BAD_REQUEST)                     
            elif teams_id:
                for team_id in teams_id:
                    try:
                        team = Team.objects.get(id=team_id)
                        if tournament.participants.filter(team=team).exists():
                            return Response({'success': False, 'message': 'Переданная команда уже учавствует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 
                        if tournament.teams_requests.contains(team):
                            tournament.teams_requests.remove(team)
                        new_participant = Participant.objects.create(team=team)
                        tournament.participants.add(new_participant)
                    except:
                        return Response({'success': False, 'message': 'Команды с переданным team id не существует!'}, status=status.HTTP_400_BAD_REQUEST)             

            return Response({'success': True, 'message': 'Пользователь добавлен на матч!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Турнира или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 
        

class AcceptTournament(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Принять турнир как модератор',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id турнира"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Успешно принят матч!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]

            tournament = Tournament.objects.get(id=tournament_id)
            
            if request.user.role == 3: # admin
                tournament.verified = True
                tournament.save()
            else:
                return Response({'success': False, 'message': 'Принять или Отклонить матч может только Админ!'}, status=status.HTTP_401_UNAUTHORIZED) 

            return Response({'success': True, 'message': 'Успешно принят турнин!'}, status=status.HTTP_200_OK) 

        except:
            return Response({'success': False, 'message': 'Турнира с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class DeclineTournament(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Отклонить турнир как модератор',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['tournament'],
            properties={
                'tournament': openapi.Schema(type=openapi.TYPE_INTEGER, description="id турнира"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Успешно принят матч!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def post(self, request):
        try:
            data = json.loads(request.body)
            tournament_id = data["tournament"]

            tournament = Tournament.objects.get(id=tournament_id)
            
            if request.user.role == 3: # admin
                tournament.delete()
            else:
                return Response({'success': False, 'message': 'Принять или Отклонить матч может только Админ!'}, status=status.HTTP_401_UNAUTHORIZED) 

            return Response({'success': True, 'message': 'Успешно отклонен турнир!'}, status=status.HTTP_200_OK) 

        except:
            return Response({'success': False, 'message': 'Турнира с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class GetTournamentsPrices(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Получить количество турниров для разлинчых диапозонов призовых фондов и вступительных взносов',                
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "prize_pool": [
                            {
                                "start_price": 5000,
                                "end_price": 10000,
                                "count": 12
                            },
                            {
                                "start_price": 10000,
                                "end_price": 15000,
                                "count": 21
                            },
                        ],  
                        'enter_price': [
                            {
                                "start_price": 5000,
                                "end_price": 10000,
                                "count": 12
                            },
                            {
                                "start_price": 10000,
                                "end_price": 15000,
                                "count": 21
                            },
                        ],  
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Не авторизован!'                      
                    },                    
                }
            ),            
    })

    def get(self, request):
        tournaments = Tournament.objects.all()

        min_prize = tournaments.aggregate(min_price=Min('prize_pool'))['min_price']
        max_prize = tournaments.aggregate(max_price=Max('prize_pool'))['max_price']
        min_enter = tournaments.aggregate(min_price=Min('enter_price'))['min_price']
        max_enter = tournaments.aggregate(max_price=Max('enter_price'))['max_price']

        min_prize = min_prize if min_prize else 0
        max_prize = max_prize if max_prize else 0
        min_enter = min_enter if min_enter else 0
        max_enter = max_enter if max_enter else 0

        num_intervals = 20
        prize_interval_size = (max_prize - min_prize) / num_intervals
        enter_interval_size = (max_enter - min_enter) / num_intervals

        prize_pool = []
        enter_price = []

        for i in range(num_intervals):
            start_prize = min_prize + i * prize_interval_size
            end_prize = start_prize + prize_interval_size
            count_prize = tournaments.filter(prize_pool__gte=start_prize, prize_pool__lte=end_prize).count()

            prize_pool.append({
                "start_price": start_prize,
                "end_price": end_prize,
                "count": count_prize
            })

            start_enter = min_enter + i * enter_interval_size
            end_enter = start_enter + enter_interval_size
            count_enter = tournaments.filter(enter_price__gte=start_enter, enter_price__lte=end_enter).count()

            enter_price.append({
                "start_price": start_enter,
                "end_price": end_enter,
                "count": count_enter
            })

        return Response({'prize_pool': prize_pool, 'enter_price': enter_price}, status=200)