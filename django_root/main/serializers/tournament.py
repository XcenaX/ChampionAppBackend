from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from main.all_models.team import Team
from main.all_models.tournament import StageResult, Tournament, TournamentStage, Participant, Match, TournamentPhoto

from main.models import User
from main.serializers.sport import SportField, TournamentListSportSerializer

from main.services.tournament import create_double_elimination_bracket, create_leaderboard_bracket, create_round_robin_bracket, create_single_elimination_bracket, create_swiss_bracket, create_round_robin_bracket_2step

from main.serializers.user import AmateurMatchUserSerializer, TournamentListUserSerializer, TournamentUserSerializer, UserSerializer

from django.db import transaction

from main.services.img_functions import _decode_photo

from main.enums import REGISTER_OPEN_UNTIL

from main.serializers.team import TeamSerializer


class TournamentListTeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['logo']


class ParticipantSerializer(serializers.ModelSerializer):
    user = AmateurMatchUserSerializer(many=False, required=False)
    team = TeamSerializer(many=False, required=False)
    score = serializers.FloatField(required=False)
    
    class Meta:
        model = Participant
        fields = ('user', 'team', 'score')


class ParticipantTournamentListSerializer(serializers.ModelSerializer):
    user = TournamentListUserSerializer(many=False, required=False)
    team = TournamentListTeamSerializer(many=False, required=False)
    
    class Meta:
        model = Participant
        fields = ('user', 'team')


class NextMatchSerializer(serializers.ModelSerializer):
    participant1 = ParticipantSerializer(many=False, required=False)
    participant2 = ParticipantSerializer(many=False, required=False)
    winner = ParticipantSerializer(many=False, required=False)
    participants = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    scheduled_start = serializers.DateTimeField()
    
    class Meta:
        model = Match
        fields = ['scheduled_start', 'actual_start', 'actual_end', 'status',
                  'participant1', 'participant2', 'winner', 'participants']


class MatchSerializer(serializers.ModelSerializer):
    participant1 = ParticipantSerializer(many=False, required=False)
    participant2 = ParticipantSerializer(many=False, required=False)
    winner = ParticipantSerializer(many=False, required=False)
    participants = serializers.ListField(child=serializers.IntegerField(), write_only=True)
    scheduled_start = serializers.DateTimeField()
    actual_start = serializers.DateTimeField(required=False)
    actual_end = serializers.DateTimeField(required=False)
    next_match = NextMatchSerializer(many=False, required=False, read_only=True)
    next_lose_match = NextMatchSerializer(many=False, required=False, read_only=True)
    
    class Meta:
        model = Match
        fields = ['scheduled_start', 'actual_start', 'actual_end', 'status',
                  'participant1', 'participant2', 'participant1_score', 'participant2_score',
                  'winner', 'participants', 'next_match', 'next_lose_match']
    
    @transaction.atomic
    def create(self, validated_data):
        participants_ids = validated_data.pop('participants', [])
        teams_ids = validated_data.pop('teams', [])
        match = Match.objects.create(**validated_data)

        for user_id in participants_ids:
            participant = Participant.objects.create(user=user_id)
            match.participants.add(participant)
        
        if not participants_ids:
            for team_id in teams_ids:
                team = Participant.objects.create(team=team_id)
                match.participants.add(team)

        return match


class StageResultSerializer(serializers.ModelSerializer):
    participant = serializers.SerializerMethodField()

    def get_participant(self, obj):
        if obj.participant.user:
            return f"{obj.participant.user.surname} {obj.participant.user.first_name}"
        elif obj.participant.team:
            return f"{obj.participant.team.name}"
        else:
            return ""
            
    class Meta:
        model = StageResult
        fields = ['participant', 'score']


class TournamentStageSerializer(serializers.ModelSerializer):
    matches = MatchSerializer(many=True, read_only=True)
    results = serializers.SerializerMethodField()

    def get_results(self, obj):
        if obj.tournament.bracket != 4:
            return []
        stage_results = StageResult.objects.filter(stage=obj)
        return [StageResultSerializer(result).data for result in stage_results]

    class Meta:
        model = TournamentStage
        fields = ['id', 'name', 'start', 'end', 'matches', 'results']



class TournamentPhotoSerializer(serializers.ModelSerializer):
    photo = serializers.FileField(use_url=True)

    class Meta:
        model = TournamentPhoto
        fields = ['photo']


class TournamentListSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    participants_count = serializers.IntegerField(read_only=True)
    sport = TournamentListSportSerializer(many=False)
    photo = serializers.SerializerMethodField()
    max_participants = serializers.IntegerField(min_value=2)
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    
    class Meta:
        model = Tournament
        fields = ['id', 'name', 'start', 'end', 'enter_price', 'sport', 'photo',
                  'max_participants', 'participants', 'participants_count', 'prize_pool']

    def get_photo(self, obj):
        photo = obj.photos.first()
        return TournamentPhotoSerializer(photo).data['photo']

    def get_participants_count(self, obj):
        return Participant.objects.filter(tournament=obj).count()

    def get_participants(self, obj):
        participants = obj.participants.all()[:4]  # Ограничиваем до первых 4 участников
        return ParticipantTournamentListSerializer(participants, many=True).data
    

class TournamentSerializer(serializers.ModelSerializer):
    owner = TournamentUserSerializer(many=False, read_only=True)
    participants = ParticipantTournamentListSerializer(many=True, read_only=True)
    moderators = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    sport = SportField(many=False, read_only=False, required=True)
    photos = serializers.SerializerMethodField()
    photos_base64 = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    teams = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    players = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    stages = TournamentStageSerializer(many=True, read_only=True)

    is_registration_available = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'description', 'address', 'city', 'start', 'end', 'register_open_until', 'is_registration_available', 'owner', 'enter_price', 'sport',
                  'photos', 'photos_base64', 'max_participants', 'participants', 'moderators', 'auto_accept_participants', 'allow_not_full_teams',
                  'is_team_tournament', 'max_team_size', 'min_team_size',
                  'group_stage_win_points', 'group_stage_draw_points', 'group_stage_rounds_count',
                  'win_points', 'draw_points', 'rounds_count',
                  'final_stage_advance_count', 'participants_in_group', 'check_score_difference_on_draw',
                  'mathces_count', 'requests', 'prize_pool', 'first_place_prize', 'second_place_prize', 'third_place_prize',
                  'city', 'rules', 'tournament_type', 'bracket', 'teams', 'players', 'stages']                  

    def __init__(self, *args, **kwargs):
        super(TournamentSerializer, self).__init__(*args, **kwargs)
        required_fields = ['name', 'start', 'end', 'bracket', 'tournament_type']

        # Устанавливаем поля из списка как обязательные
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

    @transaction.atomic
    def create(self, validated_data):
        matches_data = validated_data.pop('matches', [])
        players = validated_data.pop('players', [])
        teams = validated_data.pop('teams', [])
        photos_base64 = validated_data.pop('photos_base64', [])
        
        tournament = Tournament.objects.create(**validated_data)

        participants = list(Participant.objects.filter(tournament=tournament))

        photos = []
        for photo_base64 in photos_base64:
            photo = _decode_photo(photo_base64)
            photos.append(TournamentPhoto(tournament=tournament, photo=photo))
        
        if not photos:
            sport = validated_data.get('sport')
            validated_data['photos'] = sport.image
        else:
            TournamentPhoto.objects.bulk_create(photos)

        for user_id in players:
            try:
                user = User.objects.get(id=user_id)
                Participant.objects.create(user=user, tournament=tournament)
            except:
                pass
            
        for team_id in teams:
            try:
                team = Team.objects.get(id=team_id)
                Participant.objects.create(team=team, tournament=tournament)
            except:
                pass 
        
        if not teams and not players: # Если начальные участники не переданы сетку не создаем
            return tournament

        if tournament.tournament_type == 1:  # Двуступенчатый турнир
            create_round_robin_bracket_2step(tournament)

        elif tournament.bracket == 0:  # Single Elimination
            create_single_elimination_bracket(tournament, matches_data, participants)

        elif tournament.bracket == 1:  # Double Elimination
            create_double_elimination_bracket(tournament, matches_data, participants)

        elif tournament.bracket == 2:  # Round Robin
            create_round_robin_bracket(tournament, matches_data, participants)
        
        elif tournament.bracket == 3:  # Swiss or Leaderboard
            create_swiss_bracket(tournament, matches_data, participants)

        elif tournament.bracket == 4:
            create_leaderboard_bracket(tournament)

        tournament.save()
        return tournament

    def update(self, instance, validated_data):
        photo_base64 = validated_data.pop('photo_base64', None)
        if photo_base64:
            instance.photo.delete()
            instance.photo = self._decode_photo(photo_base64)
        return super().update(instance, validated_data)

    def get_moderators(self, obj):
        moderators_data = [UserSerializer(user).data for user in obj.moderators.all()]
        return moderators_data

    def get_requests(self, obj):
        requests_data = []
        for request in obj.users_requests.all():
            requests_data.append(AmateurMatchUserSerializer(request).data)
        for request in obj.teams_requests.all():
            requests_data.append(TeamSerializer(request).data)
        return requests_data

    def get_is_registration_available(self, obj):
        REGISTER_OPEN_UNTIL_DICT = dict(REGISTER_OPEN_UNTIL)
        registration_end_time = obj.start - REGISTER_OPEN_UNTIL_DICT.get(obj.register_open_until, timedelta(minutes=15))
        return timezone.now() < registration_end_time

    def get_photos(self, obj):
        photos_data = [TournamentPhotoSerializer(photo).data['photo'] for photo in obj.photos.all()]
        return photos_data