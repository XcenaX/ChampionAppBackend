from main.all_models.tournament import Match, Tournament, Team, TournamentPlace, TournamentStage

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

from main.serializers.tournament import TournamentSerializer

import json

from django.shortcuts import get_object_or_404

class TournamentViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TournamentFilter
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch']
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

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
                #'auto_accept_participants': openapi.Schema(type=openapi.TYPE_INTEGER, description='Автоматически принимать всех участников'),
                                
            },
            required=['name', 'start', 'enter_price', 'sport', 'max_participants']
        )
    )
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        self.send_email_to_participants(instance)

    def send_email_to_participants(self, match):
        participants = match.participants.all()        
        recipient_list = [participant.email for participant in participants if participant.email]
        
        if recipient_list:            
            send_mail(
                'ChampionApp. Турнир "{match.name}" был обновлен. Пожалуйста, проверьте детали.',
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
                    )
                )
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

            for match_data in matches_data:
                match = get_object_or_404(Match, pk=match_data.get("id"))
                
                match.scheduled_start = match_data.get("scheduled_start", match.scheduled_start)
                match.actual_start = match_data.get("actual_start", match.actual_start)
                match.actual_end = match_data.get("actual_end", match.actual_end)
                
                if "participant_1_score" in match_data and "participant_2_score" in match_data:
                    participant_1_score = match_data.get("participant_1_score")
                    participant_2_score = match_data.get("participant_2_score")
                    match.participant1.score = participant_1_score
                    match.participant2.score = participant_2_score
                    
                    if participant_1_score > participant_2_score:
                        winner = match.participant1
                        loser = match.participant2
                    else:
                        winner = match.participant2
                        loser = match.participant1

                    match.winner = winner
                    match.status = 2

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
                        pass
                    elif tournament.bracket == 3: # swiss
                        pass

                match.participant1.save()
                match.participant2.save()                
                match.save()

            return Response({'success': True, 'message': 'Турнир обновлен!'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'success': False, 'message': f'Ошибка при обновлении: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)