from main.all_models.tournament import Tournament, Team, TournamentPlace, TournamentStage

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
