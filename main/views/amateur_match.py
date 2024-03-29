from main.all_models.match import AmateurMatch
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

class AmateurMatchViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = AmateurMatchFilter
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']
    queryset = AmateurMatch.objects.all()
    serializer_class = AmateurMatchSerializer

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING),
                'start': openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description='Дата и время начала в формате YYYY-MM-DDTHH:MM:SSZ',
                    example='2023-01-01T15:00:00Z'
                ),
                'address': openapi.Schema(type=openapi.TYPE_STRING),
                'enter_price': openapi.Schema(type=openapi.TYPE_INTEGER, description='Ставка'),
                'sport': openapi.Schema(type=openapi.TYPE_INTEGER, description='ID спорта'),
                'lat': openapi.Schema(type=openapi.FORMAT_FLOAT, description='Широта'),
                'lon': openapi.Schema(type=openapi.FORMAT_FLOAT, description='Долгота'),
                
            },
            required=['name', 'start', 'address', 'enter_price', 'sport']
        )
    )
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    