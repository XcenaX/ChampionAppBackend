from django.urls import path

from main import views

urlpatterns = [
    path('user/', views.UserDetail.as_view(), name='user_detail'),
    path('login/', views.Login.as_view(), name='login'),
    path('register/', views.Register.as_view(), name='register'),
    path('send-email/', views.SendConfirmationCode.as_view(), name='send_email'),
    path('confirm-email/', views.ConfirmCode.as_view(), name='confirm_email'),
    path('send-restore-link/', views.SendRestoreLink.as_view(), name='send_restore_link'),
]