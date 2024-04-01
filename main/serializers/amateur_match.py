from rest_framework import serializers
from main.all_models.match import AmateurMatch
from django.core.exceptions import ObjectDoesNotExist
from main.all_models.sport import Sport
from main.enums import AMATEUR_MATCH_STATUS
from main.serializers.user import AmateurMatchUserSerializer
from main.serializers.sport import SportField

import base64
from django.core.files.base import ContentFile
import uuid

class AmateurMatchSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    sport = SportField(many=False, read_only=False, required=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)
    photo = serializers.CharField(write_only=True, required=False)
    photo_base64 = serializers.CharField(write_only=True, required=False)
    max_participants = serializers.IntegerField(min_value=2)
    
    class Meta:
        model = AmateurMatch
        fields = ['name', 'start', 'address', 'lat', 'lon', 'owner', "canceled", 'enter_price', 'sport', 'auto_accept_participants', 'photo', 'photo_base64', 'max_participants', 'participants', 'requests' ]

    def _decode_photo(self, photo_base64):
        format, imgstr = photo_base64.split(';base64,')
        ext = format.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")

    def create(self, validated_data):
        photo_base64 = validated_data.pop('photo_base64', None)
        if photo_base64:
            validated_data['photo'] = self._decode_photo(photo_base64)
        else:
            sport = validated_data.get('sport')
            validated_data['photo'] = sport.image
        return super().create(validated_data)

    def update(self, instance, validated_data):
        photo_base64 = validated_data.pop('photo_base64', None)
        if photo_base64:
            instance.photo.delete()
            instance.photo = self._decode_photo(photo_base64)
        return super().update(instance, validated_data)

    def get_owner(self, obj):
        serializer = AmateurMatchUserSerializer(obj.owner)
        return serializer.data

    def get_participants(self, obj):
        participants_data = [AmateurMatchUserSerializer(participant).data for participant in obj.participants.all()]
        return participants_data

    def get_requests(self, obj):
        requests_data = [AmateurMatchUserSerializer(request).data for request in obj.requests.all()]
        return requests_data