from django.urls import path, include
from rest_framework.routers import DefaultRouter
from main.views.amateur_match import AcceptMatchRequest, AmateurMatchViewSet, DeleteMatchParticipant, JoinMatch, RefuseMatchRequest

from main.views.user import UserDetail

from main.views.auth import Login, UserExists
from main.views.auth import Register
from main.views.auth import SendConfirmationCode
from main.views.auth import SendRestoreLink
from main.views.auth import ConfirmCode

router = DefaultRouter()
router.register(r'amateur-matches', AmateurMatchViewSet)

urlpatterns = [
    path('user/', UserDetail.as_view(), name='user_detail'),
    path('user/exists/', UserExists.as_view(), name='user_exists'),
    path('login/', Login.as_view(), name='login'),
    path('register/', Register.as_view(), name='register'),
    path('send-email/', SendConfirmationCode.as_view(), name='send_email'),
    path('confirm-email/', ConfirmCode.as_view(), name='confirm_email'),
    path('send-restore-link/', SendRestoreLink.as_view(), name='send_restore_link'),

    path('amateur-matches/join/', JoinMatch.as_view(), name='join_amateur_match'),
    path('match-request/accept/', AcceptMatchRequest.as_view(), name='accept_match_request'),
    path('match-request/refuse/', RefuseMatchRequest.as_view(), name='refuse_match_request'),
    path('match-request/delete/', DeleteMatchParticipant.as_view(), name='delete_match_participant'),
    path('', include(router.urls)),
]