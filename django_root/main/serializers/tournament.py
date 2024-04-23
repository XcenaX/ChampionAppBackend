import math
from rest_framework import serializers
from main.all_models.team import Team
from main.all_models.tournament import Tournament, TournamentPlace, TournamentStage, Participant, Match

from rest_framework import serializers
from main.models import User
from main.serializers.sport import SportField

from django.core.exceptions import ObjectDoesNotExist

from main.serializers.user import AmateurMatchUserSerializer, UserSerializer
from django.core.exceptions import ObjectDoesNotExist

from django.db import transaction

from main.services.img_functions import _decode_photo

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


class TeamSerializer(serializers.ModelSerializer):
    sport = SportField(many=False, read_only=False, required=True)
    members = serializers.SerializerMethodField()

    def get_members(self, obj):
        moderators_data = [UserSerializer(user).data for user in obj.members.all()]
        return moderators_data
    
    class Meta:
        model = Team
        fields = ['id', 'sport', 'name', 'logo', 'members']


class ParticipantSerializer(serializers.ModelSerializer):
    user = AmateurMatchUserSerializer(many=False, required=False)
    team = TeamSerializer(many=False, required=False)
    
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
        fields = ['scheduled_start', 'actual_start', 'actual_end', 'status', 'participant1', 'participant2', 'winner', 'participants']


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
        fields = ['scheduled_start', 'actual_start', 'actual_end', 'status', 'participant1', 'participant2', 'participant1_score', 'participant2_score', 'winner', 'participants', 'next_match', 'next_lose_match']
    
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
    city = serializers.CharField(required=True)
    participants = serializers.SerializerMethodField()
    moderators = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    sport = SportField(many=False, read_only=False, required=True)
    photo = serializers.CharField(write_only=True, required=False)
    photo_base64 = serializers.CharField(write_only=True, required=False)
    max_participants = serializers.IntegerField(min_value=2)
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    matches = MatchSerializer(many=True, required=False)
    teams = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    players = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    stages = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'start', 'end', 'owner', 'enter_price', 'sport', 'photo', 'photo_base64', 'max_participants', 'participants', 'moderators', 'auto_accept_participants', 'is_team_tournament', 'requests', 'prize_pool', 'city', 'rules', 'matches', 'bracket', 'teams', 'players', 'stages']

    @transaction.atomic
    def create(self, validated_data):
        matches_data = validated_data.pop('matches', [])
        players = validated_data.pop('players', [])
        teams = validated_data.pop('teams', [])
        photo_base64 = validated_data.pop('photo_base64', None)
        if photo_base64:
            validated_data['photo'] = _decode_photo(photo_base64)
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
        
        if not teams and not players: # Если начальные участники не переданы сетку не создаем
            return tournament
                      
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
        if num_participants == 0:
            num_rounds = 0
        else:
            num_rounds = math.ceil(math.log2(num_participants))
        current_matches = []
        unselected_participants = list(tournament.participants.all())
        
        is_players_are_users = False
        if unselected_participants[0].user:
            is_players_are_users = True

        for round_number in range(1, num_rounds + 1):
            stage_name = self.get_stage_name(round_number, num_rounds)
            stage = TournamentStage.objects.create(name=stage_name)
            new_matches = []

            if round_number == 1:
                for match_info in matches_data:
                    scheduled_start = match_info.get('scheduled_start')
                    participants_ids = match_info.get('participants', [])
                    print(participants_ids)
                    participant1 = None
                    participant2 = None

                    if participants_ids:
                        if is_players_are_users:
                            participant1 = next((p for p in unselected_participants if p.user.id == participants_ids[0]), None)
                            participant2 = next((p for p in unselected_participants if p.user.id == participants_ids[1]), None)
                        else:
                            participant1 = next((p for p in unselected_participants if p.team.id == participants_ids[0]), None)
                            participant2 = next((p for p in unselected_participants if p.team.id == participants_ids[1]), None)

                        if participant1:
                            unselected_participants.remove(participant1)
                        if participant2:
                            unselected_participants.remove(participant2)
                    else:
                        participant1 = unselected_participants.pop() if unselected_participants else None
                        participant2 = unselected_participants.pop() if unselected_participants else None

                    match = Match.objects.create(
                        scheduled_start=scheduled_start,
                        participant1=participant1,
                        participant2=participant2
                    )
                    stage.matches.add(match)
                    new_matches.append(match)
            else:
                for i in range(0, len(current_matches), 2):
                    new_match = Match.objects.create()
                    current_matches[i].next_match = new_match
                    if i + 1 < len(current_matches):
                        current_matches[i + 1].next_match = new_match
                    current_matches[i].save()
                    if i + 1 < len(current_matches):
                        current_matches[i + 1].save()
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
    
    def create_double_elimination_bracket(self, tournament, matches_data):
        num_participants = len(tournament.participants.all())
        num_rounds_upper = math.ceil(math.log2(num_participants))
        num_rounds_lower = num_rounds_upper - 1

        unselected_participants = list(tournament.participants.all())
        
        is_players_are_users = False
        if unselected_participants[0].user:
            is_players_are_users = True

        # Списки для хранения матчей в верхней и нижней сетке
        upper_matches = [[] for _ in range(num_rounds_upper)]
        lower_matches = [[] for _ in range(num_rounds_lower + 1)]  # +1 для дополнительного раунда в нижней сетке

        
        for round_number in range(num_rounds_upper):
            stage = TournamentStage.objects.create(name=f"Верхняя сетка - Этап {round_number + 1}")
            if round_number == 0:
                # Создание начальных матчей из matches_data
                for match_info in matches_data:
                    participants_ids = match_info.get('participants', [])

                    participant1 = None
                    participant2 = None

                    if participants_ids:
                        if is_players_are_users:
                            participant1 = next((p for p in unselected_participants if p.user.id == participants_ids[0]), None)
                            participant2 = next((p for p in unselected_participants if p.user.id == participants_ids[1]), None)
                        else:
                            participant1 = next((p for p in unselected_participants if p.team.id == participants_ids[0]), None)
                            participant2 = next((p for p in unselected_participants if p.team.id == participants_ids[1]), None)

                        if participant1 in unselected_participants:
                            unselected_participants.remove(participant1)
                        if participant2 in unselected_participants:
                            unselected_participants.remove(participant2)
                    else:
                        participant1 = unselected_participants.pop() if unselected_participants else None
                        participant2 = unselected_participants.pop() if unselected_participants else None

                    match = Match.objects.create(
                        scheduled_start=match_info.get('scheduled_start'),
                        participant1=participant1,
                        participant2=participant2,                            
                    )
                    stage.matches.add(match)
                    upper_matches[0].append(match)
            else:
                # Создание следующих раундов для победителей предыдущих матчей
                for i in range(0, len(upper_matches[round_number - 1]), 2):
                    match = Match.objects.create()
                    upper_matches[round_number].append(match)
                    # Назначаем следующие матчи для победителей
                    if i < len(upper_matches[round_number - 1]) - 1:
                        upper_matches[round_number - 1][i].next_match = match
                        upper_matches[round_number - 1][i + 1].next_match = match
                        upper_matches[round_number - 1][i].save()
                        upper_matches[round_number - 1][i + 1].save()
                    stage.matches.add(match)
            tournament.stages.add(stage)

        # Обработка нижней сетки
        for round_number in range(num_rounds_lower):
            stage = TournamentStage.objects.create(name=f"Нижняя сетка - Этап {round_number + 1}")
            num_matches = max(1, len(lower_matches[round_number]) // 2)
            for _ in range(num_matches):
                match = Match.objects.create()
                stage.matches.add(match)
                lower_matches[round_number + 1].append(match)

            # Связываем проигравших с матчами в нижней сетке
            if round_number == 0:
                for i, upper_match in enumerate(upper_matches[0]):
                    if i % 2 == 0:
                        loser_match = Match.objects.create()
                        stage.matches.add(loser_match)
                        upper_match.next_lose_match = loser_match
                        upper_match.save()
                        lower_matches[0].append(loser_match)
            tournament.stages.add(stage)

        # Финал между победителями верхней и нижней сетки
        final_stage = TournamentStage.objects.create(name="Финал")
        final_match = Match.objects.create()
        upper_matches[-1][0].next_match = final_match
        lower_matches[-1][0].next_match = final_match
        upper_matches[-1][0].save()
        lower_matches[-1][0].save()
        final_stage.matches.add(final_match)
        tournament.stages.add(final_stage)

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

    def get_stages(self, obj):
        stages_data = [TournamentStageSerializer(stage).data for stage in obj.stages.all()]
        return stages_data