from rest_framework import serializers
from main.all_models.tournament import Participant
from main.all_models.match import AmateurMatch, MatchPhoto
from main.serializers.user import AmateurMatchUserSerializer
from main.serializers.sport import AmateurMatchSportSerializer, SportField
import base64
from django.core.files.base import ContentFile
import uuid

class MatchPhotoSerializer(serializers.ModelSerializer):
    photo = serializers.FileField(use_url=True)

    class Meta:
        model = MatchPhoto
        fields = ['photo']


class AmateurMatchListSerializer(serializers.ModelSerializer):
    participants_count = serializers.IntegerField(read_only=True)
    photo = serializers.SerializerMethodField()
    sport = AmateurMatchSportSerializer(many=False, read_only=True)
    max_participants = serializers.IntegerField(min_value=2)
    
    def get_participants_count(self, obj):
        return obj.participants.count()
        
    def get_photo(self, obj):
        photo = obj.photos.first()
        return MatchPhotoSerializer(photo).data['photo']

    class Meta:
        model = AmateurMatch
        fields = ['id', 'name', 'start', 'address', 'city', 'enter_price', 'sport', 'photo', 'max_participants', 'participants_count']                


class AmateurMatchSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()
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

    def get_photos(self, obj):
        photos_data = [MatchPhotoSerializer(photo).data['photo'] for photo in obj.photos.all()]
        return photos_data
    
    def get_participants(self, obj):
        participants_data = [AmateurMatchUserSerializer(participant).data for participant in obj.participants.all()]
        return participants_data

    def get_requests(self, obj):
        requests_data = [AmateurMatchUserSerializer(request).data for request in obj.requests.all()]
        return requests_data