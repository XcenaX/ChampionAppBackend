from rest_framework.response import Response
from rest_framework.views import APIView

from main.serializers.user import UserSerializer

from drf_yasg.utils import swagger_auto_schema

from rest_framework.permissions import IsAuthenticated


class UserDetail(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Получение данных о пользователе",
        responses={200: UserSerializer},        
    )

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)