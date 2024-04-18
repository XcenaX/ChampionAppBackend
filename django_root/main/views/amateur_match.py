import json
from champion_backend.settings import EMAIL_HOST_USER
from main.all_models.match import AmateurMatch
from main.models import User
from main.serializers.amateur_match import AmateurMatchSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.response import Response

from rest_framework import viewsets, status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from main.filters import AmateurMatchFilter

from rest_framework.views import APIView

from django.core.mail import send_mail


class AmateurMatchViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AmateurMatchFilter
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'patch']
    queryset = AmateurMatch.objects.all()
    serializer_class = AmateurMatchSerializer

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='Описание'),                
                'start': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Дата и время начала в формате YYYY-MM-DDTHH:MM:SSZ',
                    example='2023-01-01T15:00:00Z'
                ),
                'address': openapi.Schema(type=openapi.TYPE_STRING),
                'city': openapi.Schema(type=openapi.TYPE_STRING),
                'enter_price': openapi.Schema(type=openapi.TYPE_INTEGER, description='Ставка'),
                'sport': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID спорта'),
                'max_participants': openapi.Schema(type=openapi.TYPE_INTEGER, description='Макс кол-во участников'),
                'photos_base64': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description='Список фото матча в формате base64',
                    items=openapi.Schema(
                        type=openapi.TYPE_STRING,
                        description='Фото в формате base64'
                    )
                ),
                'auto_accept_participants': openapi.Schema(type=openapi.TYPE_INTEGER, description='Автоматически принимать всех участников'),                
                'lat': openapi.Schema(type=openapi.FORMAT_FLOAT, description='Широта'),
                'lon': openapi.Schema(type=openapi.FORMAT_FLOAT, description='Долгота'),                
            },
            required=['name', 'start', 'address', 'enter_price', 'sport', 'max_participants', 'city']
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
                'ChampionApp. Матч "{match.name}" был обновлен. Пожалуйста, проверьте детали.',
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
        return Response({"success": True}, status=status.HTTP_201_CREATED, headers=headers)


class MyMatches(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Мои матчи',                
    )

    def get(self, request):
        matches = AmateurMatch.objects.filter(owner=request.user)
        serializer = AmateurMatchSerializer(matches, many=True)
        return Response({"matches": serializer.data}, status=200)
            

class JoinMatch(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Участвовать в любительском матче',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
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
            match_id = data["match"]

            match = AmateurMatch.objects.get(id=match_id)
            
            if not match.is_full():
                if match.auto_accept_participants:
                    if match.participants.contains(request.user):
                        return Response({'success': False, 'message': 'Вы уже присоеденились к матчу!'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    match.participants.add(request.user)
                    # Может быть такая ситуация: 
                    # 1) Создается матч с отключенным авто принятием -> 
                    # 2) Пользователь подает заявку на вступление ->
                    # 3) Организатор меняет авто принятие на true ->
                    # 4) Этот же пользователь вступает в матч, но заявка остается, надо ее удалить
                    if match.requests.filter(id=request.user.id).exists():
                        match.requests.remove(request.user)
                    return Response({'success': True, 'message': 'Вы успешно присоединились к матчу!'}, status=200)
                else:
                    if match.requests.contains(request.user):
                        return Response({'success': False, 'message': 'Вы уже подали заявку на этот матч!'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    match.requests.add(request.user)
                    return Response({'success': True, 'message': 'Вы успешно подали заявку на матч!'}, status=200)
            else:
                return Response({'success': False, 'message': 'Мест на матч уже нет!'}, status=status.HTTP_400_BAD_REQUEST) 

            match.save()
            # TODO
            # сделать уведомление создателя матча, что на него откликнулись
        except:
            return Response({'success': False, 'message': 'Матча с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class LeaveMatch(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Покинуть любительский матч',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Вы успешно покинули матч!'                      
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
            match_id = data["match"]

            match = AmateurMatch.objects.get(id=match_id)
            
            if match.participants.contains(request.user):
                match.participants.remove(request.user)
                return Response({'success': True, 'message': 'Вы покинули матч!'}, status=status.HTTP_200_OK)
            else:
                return Response({'success': False, 'message': 'Пользователь не состоит в этом матче но пытается выйти из него!'}, status=status.HTTP_400_BAD_REQUEST)         
        except:
            return Response({'success': False, 'message': 'Матча с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class AcceptMatchRequest(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Принять заявку человека на любительский матч',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="id пользователя которого нужно принять на матч"),                
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
            match_id = data["match"]
            user_id = data["user"]

            match = AmateurMatch.objects.get(id=match_id)
            user = User.objects.get(id=user_id)
            
            if not match.requests.contains(user):
                return Response({'success': False, 'message': 'Переданного пользователя нет в списке заявок!'}, status=status.HTTP_400_BAD_REQUEST) 

            if match.participants.contains(user):
                return Response({'success': False, 'message': 'Переданный пользователь уже учавствует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 

            match.requests.remove(user)
            match.participants.add(user)
            match.save()

            return Response({'success': True, 'message': 'Пользователь принят на матч!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Матча или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class RefuseMatchRequest(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Отклонить заявку человека на любительский матч',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="id пользователя которому нужно отказать"),                
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
            match_id = data["match"]
            user_id = data["user"]

            match = AmateurMatch.objects.get(id=match_id)
            user = User.objects.get(id=user_id)
            
            if not match.requests.contains(user):
                return Response({'success': False, 'message': 'Переданного пользователя нет в списке заявок!'}, status=status.HTTP_400_BAD_REQUEST) 
        
            match.requests.remove(user)
            match.save()

            return Response({'success': True, 'message': 'Пользователь был отклонен!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Матча или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class DeleteMatchParticipant(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Удалить участника из любительского матча',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="id пользователя которого нужно удалить"),                
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
            match_id = data["match"]
            user_id = data["user"]

            match = AmateurMatch.objects.get(id=match_id)
            user = User.objects.get(id=user_id)
            
            if not match.participants.contains(user):
                return Response({'success': False, 'message': 'Переданного пользователя нет в списке участников!'}, status=status.HTTP_400_BAD_REQUEST) 
        
            match.participants.remove(user)
            match.save()

            return Response({'success': True, 'message': 'Пользователь был удален!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Матча или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class AddMatchParticipant(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Добавить человека на любительский матч',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
                'user': openapi.Schema(type=openapi.TYPE_INTEGER, description="id пользователя которого нужно добавить на матч"),                
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
            match_id = data["match"]
            user_id = data["user"]

            match = AmateurMatch.objects.get(id=match_id)
            user = User.objects.get(id=user_id)            

            if match.participants.contains(user):
                return Response({'success': False, 'message': 'Переданный пользователь уже учавствует в этом матче!'}, status=status.HTTP_400_BAD_REQUEST) 

            if match.requests.contains(user):
                match.requests.remove(user)

            match.participants.add(user)
            match.save()

            return Response({'success': True, 'message': 'Пользователь добавлен на матч!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Матча или пользователя с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 
        

class AcceptMatch(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Принять любительский матч как модератор',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
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
            match_id = data["match"]

            match = AmateurMatch.objects.get(id=match_id)
            
            if request.user.role == 3: # admin
                match.verified = True
                match.save()
            else:
                return Response({'success': False, 'message': 'Принять или Отклонить матч может только Админ!'}, status=status.HTTP_401_UNAUTHORIZED) 

            return Response({'success': True, 'message': 'Успешно принят матч!'}, status=status.HTTP_200_OK) 

        except:
            return Response({'success': False, 'message': 'Матча с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 


class DeclineMatch(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description='Отклонить любительский матч как модератор',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['match'],
            properties={
                'match': openapi.Schema(type=openapi.TYPE_INTEGER, description="id матча"),                
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
            match_id = data["match"]

            match = AmateurMatch.objects.get(id=match_id)
            
            if request.user.role == 3: # admin
                match.delete()
            else:
                return Response({'success': False, 'message': 'Принять или Отклонить матч может только Админ!'}, status=status.HTTP_401_UNAUTHORIZED) 

            return Response({'success': True, 'message': 'Успешно отклонен матч!'}, status=status.HTTP_200_OK) 

        except:
            return Response({'success': False, 'message': 'Матча с таким id не найдено!'}, status=status.HTTP_401_UNAUTHORIZED) 