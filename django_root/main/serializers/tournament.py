import math
from rest_framework import serializers
from main.all_models.team import Team
from main.all_models.tournament import Tournament, TournamentStage, Participant, Match

from main.models import User
from main.serializers.sport import SportField, TournamentListSportSerializer

from django.core.exceptions import ObjectDoesNotExist

from main.serializers.user import AmateurMatchUserSerializer, TournamentListUserSerializer, TournamentUserSerializer, UserSerializer
from django.core.exceptions import ObjectDoesNotExist

from django.db import transaction

from main.services.img_functions import _decode_photo

import random


class TeamSerializer(serializers.ModelSerializer):
    sport = SportField(many=False, read_only=False, required=True)
    members = serializers.SerializerMethodField()

    def get_members(self, obj):
        moderators_data = [UserSerializer(user).data for user in obj.members.all()]
        return moderators_data
    
    class Meta:
        model = Team
        fields = ['id', 'sport', 'name', 'logo', 'members']


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


class TournamentStageSerializer(serializers.ModelSerializer):
    matches = MatchSerializer(many=True, read_only=True)

    class Meta:
        model = TournamentStage
        fields = ['name', 'start', 'end', 'matches']


class TournamentListSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    participants_count = serializers.IntegerField(read_only=True)
    sport = TournamentListSportSerializer(many=False)
    photo = serializers.CharField(write_only=True, required=False)
    max_participants = serializers.IntegerField(min_value=2)
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    
    class Meta:
        model = Tournament
        fields = ['id', 'name', 'start', 'end', 'enter_price', 'sport', 'photo',
                  'max_participants', 'participants', 'participants_count', 'prize_pool']

    def get_participants_count(self, obj):
        return Participant.objects.filter(tournament=obj).count()

    def get_participants(self, obj):
        participants = obj.participants.all()[:4]  # Ограничиваем до первых 4 участников
        return ParticipantTournamentListSerializer(participants, many=True).data
    

class TournamentSerializer(serializers.ModelSerializer):
    owner = TournamentUserSerializer(many=False, required=False)
    city = serializers.CharField(required=True)
    participants = ParticipantTournamentListSerializer(many=True, read_only=True)
    moderators = serializers.SerializerMethodField()
    requests = serializers.SerializerMethodField()
    sport = SportField(many=False, read_only=False, required=True)
    photo = serializers.CharField(write_only=True, required=False)
    photo_base64 = serializers.CharField(write_only=True, required=False)
    max_participants = serializers.IntegerField(min_value=2)
    start = serializers.DateTimeField(required=True)
    end = serializers.DateTimeField(required=True)
    teams = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    players = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    stages = TournamentStageSerializer(many=True, read_only=True)
    max_team_size = serializers.IntegerField(required=False)
    min_team_size = serializers.IntegerField(required=False)

    # Swiss
    win_points = serializers.FloatField(required=False)
    draw_points = serializers.FloatField(required=False)
    rounds_count = serializers.IntegerField(required=False)

    class Meta:
        model = Tournament
        fields = ['id', 'name', 'start', 'end', 'owner', 'enter_price', 'sport',
                  'photo', 'photo_base64', 'max_participants', 'participants',
                  'moderators', 'auto_accept_participants', 'is_team_tournament',
                  'max_team_size', 'min_team_size', 'win_points', 'draw_points',
                  'rounds_count', 'requests', 'prize_pool', 'city', 'rules',
                  'bracket', 'teams', 'players', 'stages']

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
        num_participants = tournament.max_participants
        if num_participants == 0:
            num_rounds = 0
        else:
            num_rounds = math.ceil(math.log2(num_participants))
        current_matches = []
        unselected_participants = list(Participant.objects.filter(tournament=tournament))
        
        num_matches_in_round_one = num_participants // 2
        
        is_players_are_users = False
        if unselected_participants[0].user:
            is_players_are_users = True
        
        for round_number in range(1, num_rounds + 1):
            stage_name = self.get_stage_name(round_number, num_rounds)
            stage = TournamentStage.objects.create(name=stage_name, tournament=tournament)
            new_matches = []
            match_count = 0
            if round_number == 1:
                for i in range(num_matches_in_round_one):
                    match_info = matches_data[i] if i < len(matches_data) else None
                    scheduled_start = None
                    participants_ids = []
                    if match_info:
                        scheduled_start = match_info.get('scheduled_start')
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
                        participant2=participant2,
                        stage=stage
                    )
                    new_matches.append(match)
                    match_count += 1                 
            else:
                for i in range(0, len(current_matches), 2):
                    new_match = Match.objects.create(stage=stage)
                    current_matches[i].next_match = new_match
                    if i + 1 < len(current_matches):
                        current_matches[i + 1].next_match = new_match
                    current_matches[i].save()
                    if i + 1 < len(current_matches):
                        current_matches[i + 1].save()
                    new_matches.append(new_match)

            current_matches = new_matches
    
    def get_stage_name(self, round_number, num_rounds):
        if round_number == num_rounds:
            return "Финал"
        elif round_number == num_rounds - 1:
            return "Полуфинал"
        else:
            return f"Этап {round_number}"
    
    def create_double_elimination_bracket(self, tournament, matches_data):
        num_participants = tournament.max_participants
        num_rounds_upper = math.ceil(math.log2(num_participants))
        num_rounds_lower = num_rounds_upper - 1

        num_matches_in_round_one = num_participants // 2

        unselected_participants = list(Participant.objects.filter(tournament=tournament))
        
        is_players_are_users = False
        if unselected_participants[0].user:
            is_players_are_users = True

        # Списки для хранения матчей в верхней и нижней сетке
        upper_matches = [[] for _ in range(num_rounds_upper)]
        lower_matches = [[] for _ in range(num_rounds_lower + 1)]  # +1 для дополнительного раунда в нижней сетке

        
        for round_number in range(num_rounds_upper):
            stage = TournamentStage.objects.create(name=f"Верхняя сетка - Этап {round_number + 1}", tournament=tournament)
            if round_number == 0:
                # Создание начальных матчей из matches_data
                for i in range(num_matches_in_round_one):
                    match_info = matches_data[i] if i < len(matches_data) else None
                    scheduled_start = None
                    participants_ids = []
                    if match_info:
                        scheduled_start = match_info.get('scheduled_start')
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
                        scheduled_start=scheduled_start,
                        participant1=participant1,
                        participant2=participant2, 
                        stage=stage,                           
                    )
                    upper_matches[0].append(match)
            else:
                # Создание следующих раундов для победителей предыдущих матчей
                for i in range(0, len(upper_matches[round_number - 1]), 2):
                    match = Match.objects.create(stage=stage)
                    upper_matches[round_number].append(match)
                    # Назначаем следующие матчи для победителей
                    if i < len(upper_matches[round_number - 1]) - 1:
                        upper_matches[round_number - 1][i].next_match = match
                        upper_matches[round_number - 1][i + 1].next_match = match
                        upper_matches[round_number - 1][i].save()
                        upper_matches[round_number - 1][i + 1].save()

        # Обработка нижней сетки
        for round_number in range(num_rounds_lower):
            stage = TournamentStage.objects.create(name=f"Нижняя сетка - Этап {round_number + 1}", tournament=tournament)
            num_matches = max(1, len(lower_matches[round_number]) // 2)
            for _ in range(num_matches):
                match = Match.objects.create(stage=stage)
                lower_matches[round_number + 1].append(match)

            # Связываем проигравших с матчами в нижней сетке
            if round_number == 0:
                for i, upper_match in enumerate(upper_matches[0]):
                    if i % 2 == 0:
                        loser_match = Match.objects.create(stage=stage)
                        upper_match.next_lose_match = loser_match
                        upper_match.save()
                        lower_matches[0].append(loser_match)

        # Финал между победителями верхней и нижней сетки
        final_stage = TournamentStage.objects.create(name="Финал", tournament=tournament)
        final_match = Match.objects.create(stage=final_stage)
        upper_matches[-1][0].next_match = final_match
        lower_matches[-1][0].next_match = final_match
        upper_matches[-1][0].save()
        lower_matches[-1][0].save()

    def create_round_robin_bracket(self, tournament):
        participants = list(Participant.objects.filter(tournament=tournament))
        matches_count = tournament.matches_count if tournament.matches_count else 1
        
        round_number = 1

        # Генерация всех возможных матчей
        for _ in range(matches_count):
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    stage_name = f"Этап {round_number}"
                    stage = TournamentStage.objects.create(name=stage_name, tournament=tournament)                    
                    match = Match.objects.create(
                        participant1=participants[i],
                        participant2=participants[j],
                        stage=stage
                    )
                    round_number += 1

    def create_swiss_bracket(self, tournament, matches_data):
        participants = list(Participant.objects.filter(tournament=tournament))
        num_participants = len(participants)

        # Создаем только первый этап в начале турнира
        stage_name = "Этап 1"
        stage = TournamentStage.objects.create(name=stage_name, tournament=tournament)

        random.shuffle(participants)
        for i in range(0, num_participants, 2):
            if i + 1 < num_participants:
                match = Match.objects.create(
                    participant1=participants[i],
                    participant2=participants[i + 1],
                    stage=stage
                )

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
