import math
from turtle import position
from main.all_models.tournament import TournamentStage, Match, Participant, Tournament
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
    num_rounds_lower = num_rounds_upper  # Теперь раунды нижней сетки равны верхней

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

    # Создаем матчи для первого раунда верхней сетки
    for i in range(0, num_participants, 2):
        match_info = matches_data[i // 2] if matches_data and i // 2 < len(matches_data) else None
        scheduled_start = match_info.get('scheduled_start', None) if match_info else None
        participants_ids = match_info.get('participants', []) if match_info else []

        participant1 = None
        participant2 = None

        if participants_ids:
            participant1 = next((p for p in participants if p.id == participants_ids[0]), None)
            participant2 = next((p for p in participants if p.id == participants_ids[1]), None)
        else:
            participant1 = participants.pop(0) if participants else None
            participant2 = participants.pop(0) if participants else None

        match = Match.objects.create(
            stage=upper_stages[0],
            scheduled_start=scheduled_start,
            participant1=participant1,
            participant2=participant2
        )

    # Обрабатываем следующие раунды верхней сетки и связываем матчи в нижней сетке
    for round_number in range(1, num_rounds_upper):
        create_next_round_matches(upper_stages[round_number - 1], upper_stages[round_number])
        if round_number < num_rounds_lower:
            link_matches_lower_bracket(upper_stages[round_number - 1], lower_stages[round_number - 1], lower_stages[round_number])

    # Создаем финальный матч
    create_final_match(upper_stages[-1], lower_stages[-1], tournament)

def create_next_round_matches(previous_stage, next_stage):
    previous_matches = Match.objects.filter(stage=previous_stage)
    for i in range(0, len(previous_matches), 2):
        if i + 1 < len(previous_matches):
            new_match = Match.objects.create(stage=next_stage)
            previous_matches[i].next_match = new_match
            previous_matches[i + 1].next_match = new_match
            previous_matches[i].save()
            previous_matches[i + 1].save()

def link_matches_lower_bracket(previous_upper_stage, previous_lower_stage, current_lower_stage):
    previous_upper_matches = list(Match.objects.filter(stage=previous_upper_stage))

    losers_from_upper = []
    for match in previous_upper_matches:
        loser = match.participant1 if match.participant1 != match.winner else match.participant2        
        losers_from_upper.append(loser)

    # Создаем новые матчи в нижней сетке для каждого проигравшего
    for i, loser in enumerate(losers_from_upper):
        if i % 2 == 0 and i + 1 < len(losers_from_upper):
            new_match = Match.objects.create(
                stage=current_lower_stage,
                participant1=losers_from_upper[i],
                participant2=losers_from_upper[i + 1]
            )
        elif i % 2 == 0:  # Нечетное количество проигравших
            new_match = Match.objects.create(
                stage=current_lower_stage,
                participant1=losers_from_upper[i],
                participant2=None  # Временно оставим без соперника
            )


def create_final_match(upper_final_stage, lower_final_stage, tournament):
    final_stage = TournamentStage.objects.create(
        name="Финал",
        tournament=tournament,
        position=upper_final_stage.position + 1  # Позиция финала идет после последней стадии верхней сетки
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

    # Проверка, что оба матча существуют
    if not last_upper_match or not last_lower_match:
        print("Ошибка: Один из финалистов отсутствует. Проверьте предыдущие этапы турнира.")



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