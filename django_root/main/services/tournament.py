import math
from main.all_models.tournament import TournamentStage, Match, Participant
import random

def create_single_elimination_bracket(tournament, matches_data, participants):
    num_participants = tournament.max_participants
    if num_participants == 0:
        num_rounds = 0
    else:
        num_rounds = math.ceil(math.log2(num_participants))
    current_matches = []
    
    num_matches_in_round_one = num_participants // 2
    
    is_players_are_users = False
    if participants[0].user:
        is_players_are_users = True
    
    stage_position = 1
    for round_number in range(1, num_rounds + 1):
        stage_name = self.get_stage_name(round_number, num_rounds)
        stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=stage_position)
        stage_position += 1

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
                        participant1 = next((p for p in participants if p.user.id == participants_ids[0]), None)
                        participant2 = next((p for p in participants if p.user.id == participants_ids[1]), None)
                    else:
                        participant1 = next((p for p in participants if p.team.id == participants_ids[0]), None)
                        participant2 = next((p for p in participants if p.team.id == participants_ids[1]), None)

                    if participant1:
                        participants.remove(participant1)
                    if participant2:
                        participants.remove(participant2)
                else:
                    participant1 = participants.pop() if participants else None
                    participant2 = participants.pop() if participants else None

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

def get_stage_name(round_number, num_rounds):
    if round_number == num_rounds:
        return "Финал"
    elif round_number == num_rounds - 1:
        return "Полуфинал"
    else:
        return f"Этап {round_number}"

def create_double_elimination_bracket(tournament, matches_data, participants):
    num_participants = tournament.max_participants
    num_rounds_upper = math.ceil(math.log2(num_participants))
    num_rounds_lower = num_rounds_upper - 1

    num_matches_in_round_one = num_participants // 2

    # Списки для хранения матчей в верхней и нижней сетке
    upper_matches = [[] for _ in range(num_rounds_upper)]
    lower_matches = [[] for _ in range(num_rounds_lower + 1)]  # +1 для дополнительного раунда в нижней сетке

    stage_position = 1
    for round_number in range(num_rounds_upper):
        stage = TournamentStage.objects.create(name=f"Верхняя сетка - Этап {round_number + 1}", tournament=tournament, position=stage_position)
        stage_position += 1

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
                    if tournament.is_team_tournament:                        
                        participant1 = next((p for p in participants if p.team.id == participants_ids[0]), None)
                        participant2 = next((p for p in participants if p.team.id == participants_ids[1]), None)
                    else:
                        participant1 = next((p for p in participants if p.user.id == participants_ids[0]), None)
                        participant2 = next((p for p in participants if p.user.id == participants_ids[1]), None)

                    if participant1 in participants:
                        participants.remove(participant1)
                    if participant2 in participants:
                        participants.remove(participant2)
                else:
                    participant1 = participants.pop() if participants else None
                    participant2 = participants.pop() if participants else None

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

def create_round_robin_bracket(tournament, participants):
    matches_count = tournament.matches_count if tournament.matches_count else 1
    
    for position in range(matches_count):
        stage_name = f"Этап {position+1}"
        stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=position+1)                    
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                Match.objects.create(
                    participant1=participants[i],
                    participant2=participants[j],
                    stage=stage
                )

def create_round_robin_bracket_2step(tournament):
    groups_count = tournament.max_participants // tournament.participants_in_group
    splitted_participants = tournament.get_participants_for_groups(groups_count)
    position = 1
    for participants in range(splitted_participants):
        matches_count = tournament.matches_count if tournament.matches_count else 1
        
        for _ in range(matches_count):
            stage_name = f"Групповой Этап {position}"
            stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=position)                    
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    Match.objects.create(
                        participant1=participants[i],
                        participant2=participants[j],
                        stage=stage
                    )
            position += 1

def create_swiss_bracket(tournament, matches_data, participants):
    num_participants = len(participants)

    is_players_are_users = False
    if participants[0].user:
        is_players_are_users = True

    stage_name = "Этап 1"
    stage = TournamentStage.objects.create(name=stage_name, tournament=tournament)

    random.shuffle(participants)
    for i in range(0, num_participants, 2):
        if i + 1 < num_participants:
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
                    participant1 = next((p for p in participants if p.user.id == participants_ids[0]), None)
                    participant2 = next((p for p in participants if p.user.id == participants_ids[1]), None)
                else:
                    participant1 = next((p for p in participants if p.team.id == participants_ids[0]), None)
                    participant2 = next((p for p in participants if p.team.id == participants_ids[1]), None)

                if participant1 in participants:
                    participants.remove(participant1)
                if participant2 in participants:
                    participants.remove(participant2)
            else:
                participant1 = participants.pop() if participants else None
                participant2 = participants.pop() if participants else None
            
            Match.objects.create(
                participant1=participant1,
                participant2=participant2,
                scheduled_start=scheduled_start,
                stage=stage
            )

def create_leaderboard_bracket(tournament):
    # Каждый этап будет как событие(тур) турнира
    rounds_count = max(tournament.rounds_count, 1)
    for i in range(1, rounds_count+1):
        stage_name = f"Этап {i}"
        TournamentStage.objects.create(name=stage_name, tournament=tournament, position=i)            

def create_new_swiss_round(stage, tournament):
    participants = Participant.objects.filter(tournament=tournament)
    # Сортировка участников по их текущему счету в убывающем порядке
    participants.sort(key=lambda x: x.score, reverse=True)

    # Организация пар на основе текущих результатов
    # Используем жадный метод для создания пар, чтобы максимально сбалансировать уровень соперников
    used = set()
    pairs = []

    for participant in participants:
        if participant not in used:
            best_match = None
            # Ищем наиболее подходящего соперника, не игравшего с данным участником
            for potential_opponent in participants:
                if potential_opponent not in used and potential_opponent != participant and not tournament.have_played(participant, potential_opponent):
                    best_match = potential_opponent
                    break
            if best_match:
                pairs.append((participant, best_match))
                used.add(participant)
                used.add(best_match)

    # Создаем матчи на основе сформированных пар
    for participant1, participant2 in pairs:
        match = Match.objects.create(
            participant1=participant1,
            participant2=participant2,
            stage=stage                
        )

def assign_final_positions(tournament):
    participants = Participant.objects.filter(tournament=tournament)
    if tournament.check_score_difference_on_draw:
        participants = sorted(participants, key=lambda x: (x.score, x.get_score_difference()), reverse=True)
    else:
        participants = participants.order_by('-score')

    for index, participant in enumerate(participants, start=1):
        participant.place = index
        participant.save()

def assign_final_positions_elimination(tournament, active_stage):
    last_match = Match.objects.filter(stage=active_stage).last()
    if not last_match.status == 2:
        return
    participants = list(Participant.objects.filter(tournament=tournament))
    if last_match.winner:
        last_match.winner.participant.place = 1
        last_match.winner.participant.save()
        participants.remove(last_match.winner.participant)
    
    for index, participant in enumerate(participants, start=2):
        participant.place = index
        participant.save()