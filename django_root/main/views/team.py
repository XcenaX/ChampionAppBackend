from main.all_models.tournament import Team

from champion_backend.settings import EMAIL_HOST_USER
from main.models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.response import Response

from rest_framework import viewsets, status

from main.filters import TeamFilter

from rest_framework.views import APIView

from main.serializers.team import TeamListSerializer, TeamSerializer


class TeamViewSet(viewsets.ModelViewSet):
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TeamFilter
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post']
    queryset = Team.objects.select_related('sport').prefetch_related("members")
    # serializer_class = TeamSerializer

    def __init__(self, *args, **kwargs):
        super(TeamViewSet, self).__init__(*args, **kwargs)
        self.serializer_action_classes = {
            'list': TeamListSerializer,
            'create': TeamSerializer,
            'retrieve': TeamSerializer,
            'update': TeamSerializer,
            'partial_update': TeamSerializer,
            'destroy': TeamSerializer,
        }
    
    def get_serializer_class(self, *args, **kwargs):
        kwargs['partial'] = True
        try:
            return self.serializer_action_classes[self.action]
        except (KeyError, AttributeError):
            return super(TeamViewSet, self).get_serializer_class()

    def perform_create(self, serializer):
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

