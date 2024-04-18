import json
from django.http import JsonResponse
from django.conf import settings
import os
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class CityRequest(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        file_path = os.path.join(settings.BASE_DIR, 'static', 'cities.json')

        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return JsonResponse(data)