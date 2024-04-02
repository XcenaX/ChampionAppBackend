from rest_framework import serializers
from main.all_models.tournament import Tournament, TournamentPlace, TournamentStage, MatchParticipant, Match

from rest_framework import serializers
from main.all_models.sport import Sport
from main.models import User
from main.serializers.sport import SportField

import base64
from django.core.files.base import ContentFile
import uuid
from django.core.exceptions import ObjectDoesNotExist

from main.serializers.user import AmateurMatchUserSerializer
from django.core.exceptions import ObjectDoesNotExist

class TournamentPlaceField(serializers.RelatedField):
    queryset = TournamentPlace.objects.all()
    
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        try:
            return TournamentPlace.objects.get(id=data)
        except ObjectDoesNotExist:
            raise serializers.ValidationError('Такой вид спорта не найден.')
        except TypeError:
            raise serializers.ValidationError('Неправильный формат данных для вида спорта.')


class MatchSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True)

    class Meta:
        model = Match
        fields = ['scheduled_start', 'participants']
    
    def create(self, validated_data):
        participants_ids = validated_data.pop('participants', [])
        match = Match.objects.create(**validated_data)
        for user_id in participants_ids:
            participant = MatchParticipant.objects.create(participant=user_id)
            match.participants.add(participant)
        return match

class TournamentStageSerializer(serializers.ModelSerializer):
    matches = MatchSerializer(many=True)

    class Meta:
        model = TournamentStage
        fields = ['name', 'start', 'end', 'matches']


class TournamentSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    place = TournamentPlaceField(many=False, read_only=False, required=True)
    participants = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    sport = SportField(many=False, read_only=False, required=True)
    photo = serializers.CharField(write_only=True, required=False)
    photo_base64 = serializers.CharField(write_only=True, required=False)
    max_participants = serializers.IntegerField(min_value=2)
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    stages = TournamentStageSerializer(many=True, required=False)

    class Meta:
        model = Tournament
        fields = ['name', 'start', 'end', 'owner', 'enter_price', 'sport', 'photo', 'photo_base64', 'max_participants', 'participants', 'requests', 'prize_pool', 'place', 'rules', 'stages']

    def _decode_photo(self, photo_base64):
        format, imgstr = photo_base64.split(';base64,')
        ext = format.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")

    def create(self, validated_data):
        stages_data = validated_data.pop('stages', [])
        photo_base64 = validated_data.pop('photo_base64', None)
        if photo_base64:
            validated_data['photo'] = self._decode_photo(photo_base64)
        else:
            sport = validated_data.get('sport')
            validated_data['photo'] = sport.image
        
        tournament = Tournament.objects.create(**validated_data)
        stages = self.create_stages(tournament, stages_data)
        
        for stage in stages:
            tournament.stages.add(stage)

        return tournament

    def create_stages(self, tournament, stages_data):
        stages = []
        for stage_data in stages_data:
            matches_data = stage_data.pop('matches', [])
            stage = TournamentStage.objects.create(**stage_data)
            matches = self.create_matches(stage, matches_data)
            
            for match in matches:
                stage.matches.add(match)
            
            stages.append(stage)
        return stages

    def create_matches(self, stage, matches_data):
        created_matches = []
        for match_data in matches_data:
            participants_data = match_data.pop('participants', [])
            match = Match.objects.create(**match_data)
            participants = self.create_match_participants(match, participants_data)
            
            for participant in participants:
                match.participants.add(participant)
                
            created_matches.append(match)
        return created_matches

    def create_match_participants(self, match, participants_data):
        participants = []
        for user in participants_data:
            participant = MatchParticipant.objects.create(participant=user)
            participants.append(participant)
        return participants

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