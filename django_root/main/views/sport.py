from main.all_models.sport import Sport
from main.serializers.sport import SportSerializer
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets

# from drf_yasg.utils import swagger_auto_schema
# from drf_yasg import openapi


class SportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']
    queryset = Sport.objects.all()
    serializer_class = SportSerializer