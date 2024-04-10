import math
import random
from rest_framework import serializers
from main.all_models.team import Team
from main.all_models.tournament import Tournament, TournamentPlace, TournamentStage, Participant, Match

from rest_framework import serializers
from main.all_models.sport import Sport
from main.models import User
from main.serializers.sport import SportField

import base64
from django.core.files.base import ContentFile
import uuid
from django.core.exceptions import ObjectDoesNotExist

from main.serializers.user import AmateurMatchUserSerializer, ParticipantSerializer
from django.core.exceptions import ObjectDoesNotExist

from django.db import transaction

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
    participant1 = ParticipantSerializer(many=False, required=False)
    participant2 = ParticipantSerializer(many=False, required=False)
    winner = ParticipantSerializer(many=False, required=False)
    participants = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    scheduled_start = serializers.DateTimeField()
    
    class Meta:
        model = Match
        fields = ['scheduled_start', 'actual_start', 'status', 'duration', 'participant1', 'participant2', 'winner', 'participants']
    
    @transaction.atomic
    def create(self, validated_data):
        participants_ids = validated_data.pop('participants', [])
        teams_ids = validated_data.pop('teams', [])
        match = Match.objects.create(**validated_data)

        for user_id in participants_ids:
            participant = Participant.objects.create(participant=user_id)
            match.participants.add(participant)
        
        if not participants_ids:
            for team_id in teams_ids:
                team = Participant.objects.create(team=team_id)
                match.participants.add(team)

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
    matches = MatchSerializer(many=True, required=False)
    teams = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    players = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    stages = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = ['name', 'start', 'end', 'owner', 'enter_price', 'sport', 'photo', 'photo_base64', 'max_participants', 'participants', 'requests', 'prize_pool', 'place', 'rules', 'matches', 'bracket', 'teams', 'players', 'stages']

    def _decode_photo(self, photo_base64):
        format, imgstr = photo_base64.split(';base64,')
        ext = format.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f"{uuid.uuid4()}.{ext}")

    @transaction.atomic
    def create(self, validated_data):
        matches_data = validated_data.pop('matches', [])
        players = validated_data.pop('players', [])
        teams = validated_data.pop('teams', [])
        photo_base64 = validated_data.pop('photo_base64', None)
        if photo_base64:
            validated_data['photo'] = self._decode_photo(photo_base64)
        else:
            sport = validated_data.get('sport')
            validated_data['photo'] = sport.image
        
        tournament = Tournament.objects.create(**validated_data)
        
        for user_id in players:
            participant = None
            try:
                user = User.objects.get(id=user_id)
                participant = Participant.objects.create(user=user)
                tournament.participants.add(participant)
            except:
                pass
            
        for team_id in teams:
            participant = None
            try:
                team = Team.objects.get(id=team_id)
                participant = Participant.objects.create(team=team)
                tournament.participants.add(participant)
            except:
                pass 
                                    
        if tournament.bracket == 0:  # Single Elimination
            self.create_single_elimination_bracket(tournament, matches_data)

        elif tournament.bracket == 1:  # Double Elimination
            self.create_double_elimination_bracket(tournament, matches_data)

        elif tournament.bracket == 2:  # Round Robin
            self.create_round_robin_bracket(tournament, matches_data)
        
        elif tournament.bracket == 3:  # Swiss
            self.create_swiss_bracket(tournament, matches_data)

        tournament.save()
        return tournament

    def create_single_elimination_bracket(self, tournament, matches_data):
        num_participants = len(tournament.participants.all())
        num_rounds = math.ceil(math.log2(num_participants))
        current_matches = []

        for round_number in range(1, num_rounds + 1):
            stage_name = self.get_stage_name(round_number, num_rounds)
            stage = TournamentStage.objects.create(name=stage_name)
            new_matches = []

            if round_number == 1:
                # Случайный выбор участников для первого раунда, если не указаны
                unselected_participants = list(tournament.participants.all())
                random.shuffle(unselected_participants)

                while unselected_participants:
                    participant1 = unselected_participants.pop() if unselected_participants else None
                    participant2 = unselected_participants.pop() if unselected_participants else None

                    match = Match.objects.create(
                        participant1=participant1,
                        participant2=participant2
                    )
                    new_matches.append(match)
                    stage.matches.add(match)
            else:
                for match in current_matches:
                    new_match = Match.objects.create()
                    match.next_match = new_match
                    match.save()
                    new_matches.append(new_match)
                    stage.matches.add(new_match)

            current_matches = new_matches
            tournament.stages.add(stage)

    def get_stage_name(self, round_number, num_rounds):
        if round_number == num_rounds:
            return "Финал"
        elif round_number == num_rounds - 1:
            return "Полуфинал"
        else:
            return f"Этап {round_number}"
    
    def create_double_elimination_bracket(self, tournament, stages_data):
        pass

    def create_round_robin_bracket(self, tournament, stages_data):
        pass

    def create_swiss_bracket(self, tournament, stages_data):
        pass

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
        participants_data = [ParticipantSerializer(participant).data for participant in obj.participants.all()]
        return participants_data

    def get_requests(self, obj):
        requests_data = [AmateurMatchUserSerializer(request).data for request in obj.requests.all()]
        return requests_data

    def get_stages(self, obj):
        stages_data = [TournamentStageSerializer(stage).data for stage in obj.stages.all()]
        return stages_data