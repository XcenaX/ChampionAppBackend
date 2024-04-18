from rest_framework import serializers
from main.all_models.match import AmateurMatch, MatchPhoto
from django.core.exceptions import ObjectDoesNotExist
from main.all_models.sport import Sport
from main.enums import AMATEUR_MATCH_STATUS
from main.serializers.user import AmateurMatchUserSerializer
from main.serializers.sport import SportField, SportSerializer

import base64
from django.core.files.base import ContentFile
import uuid

class MatchPhotoSerializer(serializers.ModelSerializer):
    photo = serializers.FileField(use_url=True)

    class Meta:
        model = MatchPhoto
        fields = ['photo']

class AmateurMatchSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    photos = MatchPhotoSerializer(many=True, read_only=True)
    photos_base64 = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    sport = SportField(many=False, read_only=False, required=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)
    max_participants = serializers.IntegerField(min_value=2)
    
    class Meta:
        model = AmateurMatch
        fields = ['id', 'name', 'description', 'start', 'address', 'city', 'lat', 'lon', 'owner', "canceled", 'enter_price', 'sport', 'auto_accept_participants', 'photos', 'photos_base64', 'max_participants', 'participants', 'requests' ]                
    
    def _decode_photo(self, photo_base64):
        format, imgstr = photo_base64.split(';base64,')
        ext = format.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")

    def create(self, validated_data):
        photos_base64 = validated_data.pop('photos_base64', [])
        match = super().create(validated_data)
        photos = []
        for photo_base64 in photos_base64:
            photo = self._decode_photo(photo_base64)
            photos.append(MatchPhoto(match=match, photo=photo))
        MatchPhoto.objects.bulk_create(photos)  # Более эффективное создание записей
        return match


    def update(self, instance, validated_data):
        photos_base64 = validated_data.pop('photos_base64', [])
        # Удаляем старые фотографии, если были предоставлены новые
        if photos_base64:
            instance.photos.all().delete()
            for photo_base64 in photos_base64:
                photo = self._decode_photo(photo_base64)
                MatchPhoto.objects.create(match=instance, photo=photo)
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