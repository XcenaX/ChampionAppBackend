import math
from turtle import position
from main.all_models.tournament import StageResult, TournamentStage, Match, Participant, Tournament
import random

def create_single_elimination_bracket(tournament, matches_data, participants):
    num_participants = tournament.max_participants
    if num_participants == 0:
        num_rounds = 0
    else:
        num_rounds = math.ceil(math.log2(num_participants))
    current_matches = []
    
    num_matches_in_round_one = num_participants // 2
    
    stage_position = 1
    for round_number in range(1, num_rounds + 1):
        stage_name = get_stage_name(round_number, num_rounds)
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
                    if tournament.is_team_tournament:
                        participant1 = next((p for p in participants if p.team.id == participants_ids[0]), None)
                        participant2 = next((p for p in participants if p.team.id == participants_ids[1]), None)
                    else:
                        participant1 = next((p for p in participants if p.user.id == participants_ids[0]), None)
                        participant2 = next((p for p in participants if p.user.id == participants_ids[1]), None)

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
    num_participants = len(participants)
    num_rounds_upper = math.ceil(math.log2(num_participants))
    num_rounds_lower = 2 * (num_rounds_upper) - 2
    # Создаем этапы верхней и нижней сетки
    upper_stages = [
        TournamentStage.objects.create(
            name=f"Верхняя сетка - Этап {i + 1}", tournament=tournament, position=(i * 2 + 1)
        ) for i in range(num_rounds_upper)
    ]

    lower_stages = [
        TournamentStage.objects.create(
            name=f"Нижняя сетка - Этап {i + 1}", tournament=tournament, position=(i * 2 + 2)
        ) for i in range(num_rounds_lower)
    ]

    lower_stages[-1].position -= 1
    lower_stages[-1].save()

    # Создаем матчи для первого раунда верхней сетки
    for i in range(0, num_participants, 2):
        participants_ids = matches_data[i // 2]['participants'] if i // 2 < len(matches_data) else None

        participant1 = None
        participant2 = None

        if participants_ids:
            participant1 = next((p for p in participants if p.id == participants_ids[0]), None)
            participant2 = next((p for p in participants if p.id == participants_ids[1]), None)
        else:
            participant1 = participants.pop(0) if participants else None
            participant2 = participants.pop(0) if participants else None

        Match.objects.create(
            stage=upper_stages[0],
            scheduled_start=matches_data[i // 2].get('scheduled_start', None),
            participant1=participant1,
            participant2=participant2
        )

    # Матчи для верхней сетки
    for stage_index in range(1, num_rounds_upper):
        previous_stage_matches = Match.objects.filter(stage=upper_stages[stage_index - 1])
        for i in range(0, len(previous_stage_matches), 2):
            match = Match.objects.create(
                stage=upper_stages[stage_index]
            )
            previous_stage_matches[i].next_match = match
            previous_stage_matches[i].save()
            if len(previous_stage_matches) > 1:
                previous_stage_matches[i + 1].next_match = match
                previous_stage_matches[i + 1].save()

    # Создание матчей для нижней сетки
    for stage_index in range(num_rounds_lower):
        current_stage = lower_stages[stage_index]

        if stage_index == 0:
            # Первый этап нижней сетки - проигравшие первого раунда верхней сетки
            upper_first_round_matches = Match.objects.filter(stage=upper_stages[0])
            for i in range(0, len(upper_first_round_matches), 2):                
                new_match = Match.objects.create(stage=current_stage)
                upper_first_round_matches[i].next_lose_match = new_match
                upper_first_round_matches[i].save()
                if len(upper_first_round_matches) > 1:
                    upper_first_round_matches[i + 1].next_lose_match = new_match
                    upper_first_round_matches[i + 1].save()
        elif stage_index % 2 == 0:
            # Этапы, где лузеры играют с лузерами
            previous_lower_stage_matches = Match.objects.filter(stage=lower_stages[stage_index - 1])
            for i in range(0, len(previous_lower_stage_matches), 2):
                new_match = Match.objects.create(stage=current_stage)
                previous_lower_stage_matches[i].next_match = new_match
                previous_lower_stage_matches[i].save()
                if i + 1 < len(previous_lower_stage_matches):
                    previous_lower_stage_matches[i + 1].next_match = new_match
                    previous_lower_stage_matches[i + 1].save()
        else:
            upper_stage_losers_matches = Match.objects.filter(stage=upper_stages[stage_index // 2 + 1])
            previous_lower_stage_matches = Match.objects.filter(stage=lower_stages[stage_index - 1])
            previous_lower_stage_matches_len = len(previous_lower_stage_matches)
            i = 0
            for match in upper_stage_losers_matches:
                new_match = Match.objects.create(stage=current_stage)
                match.next_lose_match = new_match
                match.save()
                if previous_lower_stage_matches_len > i:
                    previous_lower_stage_matches[i].next_match = new_match
                    previous_lower_stage_matches[i].save()
                i += 1

    # Финальный этап
    stages_count = TournamentStage.objects.filter(tournament=tournament).count()
    final_stage = TournamentStage.objects.create(
        name="Финал", tournament=tournament, position=stages_count + 1
    )
    final_match = Match.objects.create(
        stage=final_stage,
    )

    # Связываем финальный матч с победителями сеток
    last_upper_stage_matches = Match.objects.filter(stage=upper_stages[-1])
    for match in last_upper_stage_matches:
        if match.next_match is None:
            match.next_match = final_match
            match.save()

    last_lower_stage_matches = Match.objects.filter(stage=lower_stages[-1])
    for match in last_lower_stage_matches:
        if match.next_match is None:
            match.next_match = final_match
            match.save()

    final_match.save()

def create_final_match(upper_final_stage, lower_final_stage, tournament):
    stages_count = TournamentStage.objects.filter(tournament=tournament).count()
    final_stage = TournamentStage.objects.create(
        name="Финал", tournament=tournament,
        position=stages_count+1
    )
    final_match = Match.objects.create(stage=final_stage)
    last_upper_match = Match.objects.filter(stage=upper_final_stage).order_by('id').last()
    last_lower_match = Match.objects.filter(stage=lower_final_stage).order_by('id').last()

    if last_upper_match:
        last_upper_match.next_match = final_match
        last_upper_match.save()

    if last_lower_match:
        last_lower_match.next_match = final_match
        last_lower_match.save()



def create_round_robin_bracket(tournament, participants):
    matches_count = tournament.mathces_count if tournament.mathces_count else 1
    
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

    stage_name = "Этап 1"
    stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=1)

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
    participants = list(Participant.objects.filter(tournament=tournament))
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
        Match.objects.create(
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


def assign_final_positions_leaderboard(tournament):
    participants = []
    stages = TournamentStage.objects.filter(tournament=tournament)
    
    participant_scores = {}
    
    for stage in stages:
        results = StageResult.objects.filter(stage=stage)
        for result in results:
            participant = result.participant
            if participant in participant_scores:
                participant_scores[participant] += result.score
            else:
                participant_scores[participant] = result.score
    
    sorted_participants = sorted(participant_scores.items(), key=lambda x: x[1], reverse=True)
    
    position = 1
    prev_score = None
    for participant, score in sorted_participants:
        if score != prev_score:
            position += 1
        participant.place = position
        participant.save()
        prev_score = score

    return participants


def assign_final_positions_single_elimination(tournament):
    stages = TournamentStage.objects.filter(tournament=tournament).order_by('-position')  # Получаем этапы в обратном порядке
    for place, stage in enumerate(stages, start=1):
        matches = Match.objects.filter(stage=stage)
        for current_match in matches:
            if current_match.winner:
                if not current_match.winner.place:
                    current_match.winner.place = place
                    current_match.winner.save()
                
                # Устанавливаем место для проигравшего участника
                loser = current_match.participant1 if current_match.participant1 != current_match.winner else current_match.participant2
                if loser and not loser.place:
                    loser.place = place + 1
                    loser.save()

def assign_final_positions_double_elimination(tournament):
    stages = TournamentStage.objects.filter(tournament=tournament).order_by('-position')
    for place, stage in enumerate(stages, start=1):
        matches = Match.objects.filter(stage=stage)
        for current_match in matches:
            if current_match.winner:
                if not current_match.winner.place:
                    current_match.winner.place = place
                    current_match.winner.save()
                
                # Устанавливаем место для проигравшего участника
                loser = current_match.participant1 if current_match.participant1 != current_match.winner else current_match.participant2
                if loser and not loser.place:
                    loser.place = place + 1
                    loser.save()

def print_tournament_bracket(tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        stages = TournamentStage.objects.filter(tournament=tournament).order_by('position')
        
        for stage in stages:
            print(f"Stage: {stage.name}")
            matches = Match.objects.filter(stage=stage).order_by('id')
            for match in matches:
                p1_email = match.participant1.user.email if match.participant1 and match.participant1.user else 'None'
                p2_email = match.participant2.user.email if match.participant2 and match.participant2.user else 'None'
                print(f"{p1_email}, {p2_email}\t", end="")
            print("\n")
    
    except Tournament.DoesNotExist:
        print("Tournament not found")

def print_next_matches_for_tournament(tournament_id):
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        stages = TournamentStage.objects.filter(tournament=tournament).order_by('position')
        
        print("Tournament Match Progression:")
        for stage in stages:
            print(f"\n{stage.name}:")
            matches = Match.objects.filter(stage=stage).order_by('id')
            for match in matches:
                next_win_msg = f"Win -> {match.next_match.stage.name if match.next_match else 'Final/End'} Match {match.next_match.id if match.next_match else 'N/A'}" 
                next_lose_msg = f"Lose -> {match.next_lose_match.stage.name if match.next_lose_match else 'Final/End'} Match {match.next_lose_match.id if match.next_lose_match else 'N/A'}"
                
                print(f"Match {match.id}; {next_win_msg}; {next_lose_msg};")
    
    except Tournament.DoesNotExist:
        print("Tournament not found")