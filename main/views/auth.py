from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from main.serializers.user import UserSerializer

from champion_backend.settings import REFRESH_TOKEN_LIFETIME, EMAIL_HOST_USER

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from django.contrib.auth.hashers import check_password
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist

import re
import json

from django.core.mail import send_mail

from django.template.loader import render_to_string
from django.utils.html import strip_tags

from main.all_models.user import Confirmation
from main.models import User


class Login(APIView):
    @swagger_auto_schema(
        operation_description="Получение JWT токена",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
                'password': openapi.Schema(type=openapi.TYPE_STRING, description='Пароль пользователя'),
            }
        ),
        responses={200: openapi.Response('Токен успешно получен')}
    )
    def post(self, request, *args, **kwargs):
        username = request.data['email']
        unhashed_pass = request.data['password']
        # Check username exists
        try:
            user = User.objects.get(Q(username=username) | Q(email=username))
        except ObjectDoesNotExist:
            user = None
        if not user:            
            return Response({'success': False, 'message': 'Неверное имя пользователя или пароль'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = UserSerializer(user)
        data = serializer.data
        data.pop("password", None)
        hashed_pass = user.password
        if check_password(unhashed_pass, hashed_pass):
            refresh = RefreshToken.for_user(user)
            res = {
                'success': True,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                "user": data
            }
            response = Response(res, status=200)
            response.set_cookie(
                key='refresh',
                value=str(refresh),
                expires = REFRESH_TOKEN_LIFETIME,
                httponly=True,
                samesite="None",
                secure=True
            )
            response.set_cookie(
                key='user_id',
                value=user.id,
                httponly=True,
                samesite="None",
                secure=True
            )
            return response
        else:
            return Response({'success': False, 'message': 'Неверное имя пользователя или пароль'}, status=status.HTTP_401_UNAUTHORIZED)


class UserExists(APIView):
    @swagger_auto_schema(
        operation_description="Существует ли пользователь в базе",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email пользователя'),
            }
        ),
        responses={
            200: openapi.Response('', examples={
                "application/json": {
                    "exists": True                                          
                },                    
            })
        }
    )
    def post(self, request, *args, **kwargs):
        username = request.data['email']
        
        try:
            user = User.objects.get(Q(username=username) | Q(email=username))
            return Response({'exists': True}, status=200)
        except ObjectDoesNotExist:
            return Response({'exists': True}, status=200)
            

class Register(APIView):
    @swagger_auto_schema(
        operation_description='Регистрация',        
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password', 'confirm_password'],
            properties={
                'email':openapi.Schema(type=openapi.TYPE_STRING),
                # 'phone':openapi.Schema(type=openapi.TYPE_STRING),
                'password':openapi.Schema(type=openapi.TYPE_STRING),
                'confirm_password':openapi.Schema(type=openapi.TYPE_STRING),
                'notify':openapi.Schema(type=openapi.TYPE_BOOLEAN),                
                'first_name':openapi.Schema(type=openapi.TYPE_STRING),
                'surname':openapi.Schema(type=openapi.TYPE_STRING),
                # 'degree':openapi.Schema(type=openapi.TYPE_STRING),
                # 'role':openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            "200": openapi.Response(        
                description='',        
                examples={
                    "application/json": {
                        "success": True,  
                        'message': 'Пользователь успешно создан!'                      
                    },                    
                }
            ),
            "401": openapi.Response(
                description='',                
                examples={
                    "application/json": {
                        "success": False,  
                        'message': 'Такой пользователь уже существует!'                      
                    },                    
                }
            ),            
        })
    def post(self, request):
        try:
            data = json.loads(request.body)
            first_name = data['first_name']
            surname = data['surname']
            unhashed_pass = data['password']
            confirm_pass = data['confirm_password']
            notify = data['notify']
            email = data['email']
            
            # degree = request.data['degree']
            # role = request.data['role']
        except:
            return Response({'success': False, 'message': 'Переданы не все параметры!'}, status=status.HTTP_401_UNAUTHORIZED) 
        
        if(unhashed_pass != confirm_pass):
            return Response({'success': False, 'message': 'Пароли не совпадают!'}, status=status.HTTP_401_UNAUTHORIZED) 
        
        for e in first_name + surname:
            if not e.isalnum():
                return Response({'success': False, 'message': 'ФИО не должно содержать специальных символов!'}, status=status.HTTP_401_UNAUTHORIZED) 
        
        # phone = request.data['phone']
        # replace_list = ['(', ')', '-', '+', ' ']
        # for symbol in replace_list:
        #     phone = phone.replace(symbol, '')

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response({'success': False, 'message': 'Неверный формат Email!'}, status=status.HTTP_401_UNAUTHORIZED) 

        if len(unhashed_pass) < 5:
            return Response({'success': False, 'message': 'Неверный формат пароля!'}, status=status.HTTP_401_UNAUTHORIZED) 

        if len(first_name) < 2 or len(surname) < 2:
            return Response({'success': False, 'message': 'Неверное ФИО!'}, status=status.HTTP_401_UNAUTHORIZED) 

        try:
            User.objects.get(Q(email=email) | Q(username=email))            
            return Response({'success': False, 'message': 'Такой пользователь уже существует!'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            pass
        
        new_user = User.objects.create(username=email, first_name=first_name, surname=surname, email=email, notify=notify)
        new_user.set_password(unhashed_pass)
        # assign_role(new_user, 'default')
        new_user.save()
        
        return Response({'success': True, 'message': 'Пользователь успешно создан!'}, status=200)


class SendRestoreLink(APIView):
    @swagger_auto_schema(
        operation_description='Отправить ссылку для восстановления пароля',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email'],
            properties={
                'email':openapi.Schema(type=openapi.TYPE_STRING),                
                'link':openapi.Schema(type=openapi.TYPE_STRING),                
            },
        ),
        responses={
            "200": openapi.Response(         
                description='',       
                examples={
                    "application/json": {
                        'success': True,                        
                        'message':'some message'
                    },                    
                }
            ),
            "401": openapi.Response(  
                description='',                     
                examples={
                    "application/json": {
                        'success': False,                        
                        'message':'some error'
                    },                    
                }
            ),            
        })
    def post(self, request):        
        try:
            data = json.loads(request.body)
            email = data['email']
            link = data['link']
        except:
            return Response({'success': False, 'message': 'Переданы не все параметры!'}, status=status.HTTP_401_UNAUTHORIZED) 
            
        try:
            User.objects.get(email=email)
        except:
            return Response({'success': False, 'message': 'Такой пользователь не существует!'}, status=401)
        
        html_message = render_to_string('reset_password.html', {'link': link})
        plain_message = strip_tags(html_message)
        send_mail(
            "Восстановление пароля",
            plain_message,
            EMAIL_HOST_USER,
            [email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return Response({'success': True, 'message': 'Ссылка для восстановления пароля была отправлена на ваш email!'}, status=200)


class SendConfirmationCode(APIView):
    @swagger_auto_schema(
        operation_description='Отправить код на почту',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'email_type'],
            properties={
                'email':openapi.Schema(type=openapi.TYPE_STRING),                
                'email_type':openapi.Schema(type=openapi.TYPE_INTEGER),                
            },
        ),
        responses={
            "200": openapi.Response(                
                description='',       
                examples={
                    "application/json": {
                        'success': True,
                        'code': "234763",
                        'message':'Код для подтверждения почты был отправлен на ваш email!'
                    },                    
                }
            ),
            "401": openapi.Response(     
                description='',                  
                examples={
                    "application/json": {
                        'success': False,                        
                        'message':'Такой пользователь не существует!'
                    },                    
                }
            ),            
        })
    def post(self, request): 
        try:
            data = json.loads(request.body)
            email = data['email']
            email_type = data['email_type']
        except:
            return Response({'success': False, 'message': 'Переданы не все параметры!'}, status=status.HTTP_401_UNAUTHORIZED) 

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response({'success': False, 'message': 'Неверный формат Email!'}, status=401)
        
        try:
            confirmation = Confirmation.objects.get(email=email, email_type=email_type)
            confirmation.delete()
        except:
            pass
        
        confirmation = Confirmation.objects.create(email=email, email_type=email_type)        
        
        return Response({'success': True, 'code': confirmation.code, 'message': 'Код для подтверждения почты был отправлен на ваш email!'}, status=200)


class ConfirmCode(APIView):
    @swagger_auto_schema(
        operation_description='Подтвердить код с почты',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'code'],
            properties={
                'email':openapi.Schema(type=openapi.TYPE_STRING),                
                'code':openapi.Schema(type=openapi.TYPE_STRING),                
            },
        ),
        responses={
            "200": openapi.Response(                
                description='',       
                examples={
                    "application/json": {
                        'success': True,                        
                        'message':'Email успешно подтвержден!'
                    },                    
                }
            ),
            "401": openapi.Response(     
                description='',                  
                examples={
                    "application/json": {
                        'success': False,                        
                        'message':'Неверный код!'
                    },                    
                }
            ),            
        })
    def post(self, request):                
        try:
            data = json.loads(request.body)
            email = data['email']
            code = data['code']
        except:
            return Response({'success': False, 'message': 'Переданы не все параметры!'}, status=status.HTTP_401_UNAUTHORIZED) 

        try:
            confirmation = Confirmation.objects.get(email=email, code=code)
            confirmation.delete()
        except:
            return Response({'success': False, 'message': 'Неверный код!'}, status=401)               
        
        return Response({'success': True, 'message': 'Email успешно подтвержден!'}, status=200)


class RestorePassword(APIView):
    @swagger_auto_schema(
        operation_description='Изменить пароль на новый',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password', 'confirm_password'],
            properties={
                'email':openapi.Schema(type=openapi.TYPE_STRING),                
                'password':openapi.Schema(type=openapi.TYPE_STRING),                            
                'confirm_password':openapi.Schema(type=openapi.TYPE_STRING),                            
            },
        ),
        responses={
            "200": openapi.Response(   
                description='',                    
                examples={
                    "application/json": {
                        'success': True,                        
                        'message':'Пароль успешно был изменен!'
                    },                    
                }
            ),
            "401": openapi.Response(   
                description='',                    
                examples={
                    "application/json": {
                        'success': False,                        
                        'message':'Ошибка!'
                    },                    
                }
            ),            
        })
    def post(self, request):                
        try:
            data = json.loads(request.body)
            password = data['password']
            confirm_password = data['confirm_password']
            email = data['email']
        except:
            return Response({'success': False, 'message': 'Переданы не все параметры!'}, status=status.HTTP_401_UNAUTHORIZED) 

        if password != confirm_password:
            return Response({'success': False, 'message': 'Пароли не совпадают!'}, status=401)

        try:
            user = User.objects.get(Q(email=email) | Q(username=email))
            user.set_password(password)
            return Response({'success': True, 'message': 'Пароль успешно был изменен!'}, status=200)
        except:
            return Response({'success': False, 'message': 'Пользователя с таким Email не существует!'}, status=401)
