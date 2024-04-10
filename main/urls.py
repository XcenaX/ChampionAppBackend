from django.urls import path, include
from rest_framework.routers import DefaultRouter
from main.views.amateur_match import AcceptMatch, AcceptMatchRequest, AddMatchParticipant, AmateurMatchViewSet, DeclineMatch, DeleteMatchParticipant, JoinMatch, RefuseMatchRequest

from main.views.city import CityRequest
from main.views.sport import SportViewSet
from main.views.tournament import TournamentViewSet
from main.views.user import UserDetail

from main.views.auth import Login, RestorePassword, UserExists
from main.views.auth import Register
from main.views.auth import SendConfirmationCode
from main.views.auth import SendRestoreLink
from main.views.auth import ConfirmCode

router = DefaultRouter()
router.register(r'amateur-matches', AmateurMatchViewSet)
router.register(r'tournaments', TournamentViewSet)
router.register(r'sports', SportViewSet)

urlpatterns = [
    path('user/', UserDetail.as_view(), name='user_detail'),
    path('user/exists/', UserExists.as_view(), name='user_exists'),

    path('auth/login/', Login.as_view(), name='login'),
    path('auth/register/', Register.as_view(), name='register'),
    path('auth/send-email/', SendConfirmationCode.as_view(), name='send_email'),
    path('auth/confirm-email/', ConfirmCode.as_view(), name='confirm_email'),
    path('auth/reset-password/', RestorePassword.as_view(), name='restore_password'),

    path('cities/', CityRequest.as_view(), name='cities'),

    path('amateur-matches/join/', JoinMatch.as_view(), name='join_amateur_match'),
    path('amateur-matches/accept/', AcceptMatch.as_view(), name='accept_amateur_match'),
    path('amateur-matches/decline/', DeclineMatch.as_view(), name='decline_amateur_match'),

    path('match-request/accept/', AcceptMatchRequest.as_view(), name='accept_match_request'),
    path('match-request/refuse/', RefuseMatchRequest.as_view(), name='refuse_match_request'),
    path('match-request/delete/', DeleteMatchParticipant.as_view(), name='delete_match_participant'),
    path('match-request/add/', AddMatchParticipant.as_view(), name='add_match_participant'),
    path('', include(router.urls)),
]