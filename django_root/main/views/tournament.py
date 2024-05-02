from turtle import position
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

from main.serializers.tournament import TournamentListSerializer, TournamentSerializer, TournamentStageSerializer

import json
from django.db.models import Q

from django.shortcuts import get_object_or_404

from main.services.img_functions import _decode_photo

from django.db.models import Min, Max
from django.db.models import Count

from main.services.tournament import assign_final_positions_leaderboard, create_double_elimination_bracket, create_leaderboard_bracket, create_new_swiss_round, create_round_robin_bracket, create_round_robin_bracket_2step, create_single_elimination_bracket, create_swiss_bracket

from main.services.tournament import assign_final_positions, assign_final_positions_double_elimination, assign_final_positions_single_elimination

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
        #try:
            data = json.loads(request.body)
            matches_data = data.get("matches", [])
            results_data = data.get("results", [])

            tournament = Tournament.objects.get(id=id)

            stage = tournament.get_active_stage()

            if results_data and stage:             
                for result_data in results_data:
                    participant_id = result_data.get("participant_id", None)
                    if not participant_id:
                        return Response({'success': False, 'message': 'Ошибка при обновлении: Участник с переданым participant_id не найден!'}, status=status.HTTP_400_BAD_REQUEST)

                    participant = Participant.objects.get((Q(user__id=participant_id) | Q(team__id=participant_id)) & Q(tournament=tournament))
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
                participant_1_score = match_data.get("participant_1_score", None)
                participant_2_score = match_data.get("participant_2_score", None)   
                                                         
                winner = None
                                                                                
                if participant_1_score > participant_2_score:
                    winner = match.participant1
                elif participant_1_score < participant_2_score:
                    winner = match.participant2                                         
                     
                match.winner = winner
                match.participant1_score = participant_1_score
                match.participant2_score = participant_2_score
                match.status = 2                

                match.save()                                      

            return Response({'success': True, 'message': 'Турнир обновлен!'}, status=status.HTTP_200_OK)

        # except Exception as e:
        #     return Response({'success': False, 'message': f'Ошибка при обновлении: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        

class EndTournamentStage(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Завершить этап турнира',
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Этап завершен!'                      
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

    def post(self, request, id):
        #try:
            tournament = Tournament.objects.get(id=id)
            
            if tournament.owner != request.user and not tournament.moderators.filter(id=request.user.id).exists():
                return Response({'success': False, 'message': "Только организатор или модераторы могут завершить этап!"}, status=status.HTTP_403_FORBIDDEN) 

            active_stage = tournament.get_active_stage()
            if not active_stage:
                return Response({'success': False, 'message': "Турнир уже завершен или нет активного этапа!"}, status=status.HTTP_400_BAD_REQUEST) 

            matches = Match.objects.filter(stage=active_stage)
            if not all(match.status == 2 for match in matches):  # Проверяем, завершены ли все матчи
                return Response({'success': False, 'message': "Не все матчи этапа завершены!"}, status=status.HTTP_400_BAD_REQUEST)

            if tournament.bracket == 3 and tournament.stages.count() < tournament.rounds_count:
                # Swiss or other multi-round bracket logic
                if all(match.status == 2 for match in matches):
                    stages_count = TournamentStage.objects.filter(tournament=tournament).count()
                    if stages_count < tournament.rounds_count:
                        new_stage = TournamentStage.objects.create(
                            name=f"Этап {tournament.stages.count() + 1}",
                            tournament=tournament,
                            position=stages_count+1
                        )
                        create_new_swiss_round(new_stage, tournament)
                        tournament.active_stage_position += 1
                    else:
                        assign_final_positions(tournament)
            elif tournament.bracket == 4:
                if tournament.active_stage_position == tournament.rounds_count:
                    assign_final_positions_leaderboard(tournament)
                else:
                    tournament.active_stage_position += 1

            elif not tournament.has_next_stage():
                if tournament.bracket == 0:  # Single elimination
                    assign_final_positions_single_elimination(tournament)
                elif tournament.bracket == 1:  # Double elimination
                    assign_final_positions_double_elimination(tournament)
                else:
                    assign_final_positions(tournament)
                return Response({'success': True, 'message': "Турнир завершен!"}, status=status.HTTP_200_OK)
            else:
                # Proceed to next stage
                current_stage_matches = matches
                for match in current_stage_matches:
                    self.process_match_winner_to_next_stage(match, tournament.bracket)
                tournament.active_stage_position += 1

            tournament.save()
            return Response({'success': True, 'message': "Этап турнира завершен!"}, status=status.HTTP_200_OK)
        
        # except Tournament.DoesNotExist:
        #     return Response({'success': False, 'message': "Турнир не найден!"}, status=status.HTTP_404_NOT_FOUND)
        # except Exception as error:
        #     return Response({'success': False, 'message': f'Ошибка при обновлении: {str(error)}'}, status=status.HTTP_400_BAD_REQUEST)

    def process_match_winner_to_next_stage(self, match, bracket):
        # Обновляет следующий матч с победителем текущего матча
        if match.next_match:
            if not match.next_match.participant1:
                match.next_match.participant1 = match.winner
            elif not match.next_match.participant2:
                match.next_match.participant2 = match.winner
            match.next_match.save()
        if bracket == 1:  # Double elimination logic
            if match.next_lose_match:
                loser = match.participant2 if match.participant1 == match.winner else match.participant1
                if not match.next_lose_match.participant1:
                    match.next_lose_match.participant1 = loser
                elif not match.next_lose_match.participant2:
                    match.next_lose_match.participant2 = loser
                match.next_lose_match.save()

    
    
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
                        'message': 'Вы успешно присоединились к турниру!'                      
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
                        new_participant = Participant.objects.create(user=request.user, tournament=tournament)                        
                    else:                        
                        new_participant = Participant.objects.create(team=new_team, tournament=tournament)

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
            return Response({'success': False, 'message': str(error)}, status=status.HTTP_401_UNAUTHORIZED) 


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
                team = Team.objects.get(id=team_id)     
                participants = Participant.objects.filter(team=team, tournament=tournament)   
                for participant in participants:
                    participant.delete()       
                return Response({'success': True, 'message': 'Вы покинули турнир!'}, status=status.HTTP_200_OK)
            else:
                participants = Participant.objects.filter(user=request.user, tournament=tournament)   
                for participant in participants:
                    participant.delete()                                    
                return Response({'success': True, 'message': 'Вы покинули турнир!'}, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'success': False, 'message': f'Турнира с таким id не найдено! {str(error)}'}, status=status.HTTP_401_UNAUTHORIZED) 


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
                    new_participant = Participant.objects.create(user=user, tournament=tournament)
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
                    new_participant = Participant.objects.create(team=team, tournament=tournament)
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
        operation_description='Добавить участников или команды на турнир',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['participants'],
            properties={                               
                'participants': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id пользователей или команд"),                
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

    def post(self, request, id):
        try:
            data = json.loads(request.body)
            
            participants_id = data.get("participants", [])

            tournament = Tournament.objects.get(id=id)

            if tournament.is_team_tournament:
                for team_id in participants_id:
                    try:
                        team = Team.objects.get(id=team_id)
                        if tournament.participants.filter(team=team).exists():
                            return Response({'success': False, 'message': 'Переданная команда уже учавствует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 
                        if tournament.teams_requests.contains(team):
                            tournament.teams_requests.remove(team)
                        new_participant = Participant.objects.create(team=team, tournament=tournament)
                        tournament.participants.add(new_participant)
                    except:
                        return Response({'success': False, 'message': 'Команды с переданным team id не существует!'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                for user_id in participants_id:
                    try:
                        user = User.objects.get(id=user_id)                    
                        if tournament.participants.filter(user=user).exists():
                            return Response({'success': False, 'message': 'Переданный пользователь уже учавствует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 
                        if tournament.users_requests.contains(user):
                            tournament.users_requests.remove(user)
                        new_participant = Participant.objects.create(user=user, tournament=tournament)
                        tournament.participants.add(new_participant)
                    except:
                        return Response({'success': False, 'message': 'Пользователя с переданным user id не существует!'}, status=status.HTTP_400_BAD_REQUEST)            
            
            return Response({'success': True, 'message': 'Пользователь добавлен на матч!'}, status=200)
       
        except:
            return Response({'success': False, 'message': 'Турнира или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class CreateTournamentBracket(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Создать сетку для турнира на основе текущих участников',                
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'matches': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='Список матчей для обновления',
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'scheduled_start': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='Запланированное время начала матча'),
                            'participants': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id пользователей или команд"),                                            
                        },
                        required=['id']
                    ),
                )                
            }
        ),
        responses={
            "201": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Вы успешно создали сетку турнира!'                      
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

    def post(self, request, id):
        #try:       
            data = json.loads(request.body)
            matches_data = data.get("matches", None)
            tournament = Tournament.objects.get(id=id)            

            participants = list(Participant.objects.filter(tournament=tournament))
            
            if tournament.tournament_type == 1:  # Двуступенчатый турнир
                create_round_robin_bracket_2step(tournament)

            elif tournament.bracket == 0:  # Single Elimination
                create_single_elimination_bracket(tournament, matches_data, participants)

            elif tournament.bracket == 1:  # Double Elimination
                create_double_elimination_bracket(tournament, matches_data, participants)

            elif tournament.bracket == 2:  # Round Robin
                create_round_robin_bracket(tournament, participants)
            
            elif tournament.bracket == 3:  # Swiss or Leaderboard
                create_swiss_bracket(tournament, matches_data, participants)

            elif tournament.bracket == 4:
                create_leaderboard_bracket(tournament)

            stages = TournamentStage.objects.filter(tournament=tournament).order_by("position")
            stages_serializer = TournamentStageSerializer(stages, many=True)

            return Response({'success': True, 'bracket_stages': stages_serializer.data}, status=status.HTTP_201_CREATED) 
        # except Exception as error:
        #     return Response({'success': False, 'message': str(error)}, status=status.HTTP_401_UNAUTHORIZED) 


class SetTournamentModerators(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Изменить модераторов турнира. Список модераторов заменяется на переданный',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['users'],
            properties={
                'users': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_INTEGER), description="id пользователей"),                
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

    def post(self, request, id):
        try:
            data = json.loads(request.body)
            
            users_id = data.get("users", [])

            tournament = Tournament.objects.get(id=id)

            if users_id:
                tournament.moderators.clear()
                for user_id in users_id:
                    try:
                        user = User.objects.get(id=user_id)                    
                        tournament.moderators.add(user)
                    except:
                        return Response({'success': False, 'message': 'Пользователя с переданным user id не существует!'}, status=status.HTTP_400_BAD_REQUEST)                     

            return Response({'success': True, 'message': 'Модераторы турнира изменены!'}, status=200)
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