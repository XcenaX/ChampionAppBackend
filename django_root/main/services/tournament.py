import math
from turtle import position
from main.all_models.tournament import StageResult, TournamentStage, Match, Participant, Tournament
import random

def get_participants_from_matches_data(matches_data: list, tournament, available_participants):
    match_info = None
    try:
        match_info = matches_data.pop()
    except:
        pass
    
    participants_ids = []
    if match_info:
        participants_ids = match_info.get('participants', [])
    
    extracted_participants = []
    for pid in participants_ids:
        if tournament.is_team_tournament:
            participant = next((p for p in available_participants if p.team.id == pid), None)
        else:
            participant = next((p for p in available_participants if p.user.id == pid), None)
        
        if participant:
            available_participants.remove(participant)
            extracted_participants.append(participant)
    
    while len(extracted_participants) < 2:
        if available_participants:
            extracted_participants.append(available_participants.pop())
        else:
            extracted_participants.append(None)
    
    return extracted_participants[0], extracted_participants[1], match_info

def create_single_elimination_bracket(tournament, matches_data, participants:list):
    num_participants = len(participants)
    target_participants = 2**math.ceil(math.log2(num_participants)) // 2
    if num_participants == 0:
        num_rounds = 0
    else:
        num_rounds = math.ceil(math.log2(target_participants))
    current_matches = []
    
    preliminary_needed = False
    if num_participants != target_participants:
        preliminary_needed = True
        num_preliminary_matches = num_participants - target_participants

    num_matches_in_round_one = target_participants // 2
    
    stage_position = 1
    stage_position_offset = tournament.get_stage_offset()

    if preliminary_needed:
        stage_name = get_stage_name(0, num_rounds)
        stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=stage_position + stage_position_offset)
        stage_position += 1
        for i in range(num_preliminary_matches):
            # match_info = matches_data[i] if i < len(matches_data) else None
            
            participant1, participant2, match_info = get_participants_from_matches_data(matches_data, tournament, participants)
            
            match = Match.objects.create(
                participant1=participant1,
                participant2=participant2,
                scheduled_start=match_info.get("scheduled_start", None),
                stage=stage
            )
            current_matches.append(match)

    for round_number in range(1, num_rounds + 1):
        stage_name = get_stage_name(round_number, num_rounds)
        stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=stage_position + stage_position_offset)
        stage_position += 1

        new_matches = []
        match_count = 0
        if round_number == 1:
            for i in range(num_matches_in_round_one):
                if not participants:
                    break
                # match_info = matches_data[i + num_preliminary_matches] if (i + num_preliminary_matches) < len(matches_data) else None
                participant1, participant2, match_info = get_participants_from_matches_data(matches_data, tournament, participants)

                scheduled_start = None if not match_info else match_info.get("scheduled_start", None)                

                match = Match.objects.create(
                    scheduled_start=scheduled_start,
                    participant1=participant1,
                    participant2=participant2,
                    stage=stage
                )
                new_matches.append(match)
                match_count += 1  
            
            i = 0
            if current_matches:
                for match in new_matches:
                    if not match.participant1:
                        current_matches[i].next_match = match
                        current_matches[i].save()
                        i += 1
                    if not match.participant2:
                        current_matches[i].next_match = match
                        current_matches[i].save()
                        i += 1
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

def create_double_elimination_bracket(tournament, matches_data, participants:list):
    num_participants = len(participants)
    target_participants = 2**math.ceil(math.log2(num_participants)) // 2
    num_rounds_upper = math.ceil(math.log2(target_participants))
    num_rounds_lower = 2 * (num_rounds_upper) - 2
    
    stage_position_offset = tournament.get_stage_offset() # Для Двуступенчатых турниров
    
    preliminary_needed = False
    need_create_additional_stage = False
    if num_participants != target_participants:
        preliminary_needed = True
        num_preliminary_matches = num_participants - target_participants
        need_create_additional_stage = num_preliminary_matches > target_participants // 2
        
    # Создаем этапы верхней и нижней сетки
    upper_stages = [
        TournamentStage.objects.create(
            name=f"Верхняя сетка - Этап {i + 1}", tournament=tournament, position=(i * 2 + 1) + stage_position_offset
        ) for i in range(num_rounds_upper)
    ]

    lower_stages = [
        TournamentStage.objects.create(
            name=f"Нижняя сетка - Этап {i + 1}", tournament=tournament, position=(i * 2 + 2) + stage_position_offset
        ) for i in range(num_rounds_lower)
    ]

    if target_participants != num_participants:
        position = -1
        new_upper_stage = TournamentStage.objects.create(name=f"Верхняя сетка - Предварительный Этап 1", tournament=tournament, position=position)
        # upper_stages.append(new_upper_stage)
        additional_upper_matches = []
        for i in range(num_preliminary_matches):
            participant1, participant2, match_info = get_participants_from_matches_data(matches_data, tournament, participants)
            match = Match.objects.create(
                participant1=participant1,
                participant2=participant2,
                scheduled_start=match_info.get("scheduled_start", None),
                stage=new_upper_stage
            )
            additional_upper_matches.append(match)

        position = 1
        new_lower_stage = TournamentStage.objects.create(name=f"Нижняя сетка - Предварительный Этап 2", tournament=tournament, position=position)
        # lower_stages.append(new_lower_stage)
        additional_lower_matches = []

        for i in range(min(target_participants // 2, num_preliminary_matches)):
            match = Match.objects.create(stage=new_lower_stage)
            additional_upper_matches[i].next_lose_match = match
            additional_upper_matches[i].save()
            additional_lower_matches.append(match)
        
        if need_create_additional_stage:
            upper_stages[0].position = 0
            upper_stages[0].save()
            new_upper_stage.position = -2
            new_upper_stage.save()
            position = -1
            
            new_lower_stage2 = TournamentStage.objects.create(name=f"Нижняя сетка - Предварительный Этап 1", tournament=tournament, position=position)
            # lower_stages.append(new_lower_stage2)
            new_lower_stage.position = 1
            new_lower_stage.save()           
         
            additional_upper_matches_len = len(additional_upper_matches)
            for i in range(target_participants // 2, num_preliminary_matches):
                match = Match.objects.create(stage = new_lower_stage2)
                
                next_match_set = False
                count = 0
                while not next_match_set:
                    if not additional_lower_matches[count].participant1 or not additional_lower_matches[count].participant2:
                        match.next_match = additional_lower_matches[count]
                        match.save()
                        next_match_set = True
                    count += 1

                additional_upper_matches[additional_upper_matches_len-1].next_lose_match = match
                additional_upper_matches[additional_upper_matches_len-1].save()

                additional_upper_matches[additional_upper_matches_len-2].next_lose_match = match
                additional_upper_matches[additional_upper_matches_len-2].save()

                additional_upper_matches_len -= 2

              
                

    # Фиксим позиции этапов если надо
    previous_stage = None
    for stage in TournamentStage.objects.filter(tournament=tournament).order_by("position"):
        if previous_stage:
            if stage.position - previous_stage.position != 1:
                stage.position = previous_stage.position + 1
                stage.save()
        previous_stage = stage 

    # Создаем матчи для первого раунда верхней сетки
    count = 0
    for i in range(target_participants // 2):
        participant1, participant2, match_info = get_participants_from_matches_data(matches_data, tournament, participants)
        if match_info:
            scheduled_start = match_info.get('scheduled_start', None)

        match = Match.objects.create(
            stage=upper_stages[0],
            scheduled_start=scheduled_start,
            participant1=participant1,
            participant2=participant2
        )

        if count < len(additional_upper_matches) and not participant1:            
                additional_upper_matches[count].next_match = match
                additional_upper_matches[count].save()
                count += 1
        
        if count < len(additional_upper_matches) and not participant2:            
                additional_upper_matches[count].next_match = match
                additional_upper_matches[count].save()
                count += 1

        if i < len(additional_lower_matches):
            match.next_lose_match = additional_lower_matches[i]
            match.save()

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
            count = 0
            for i in range(0, len(upper_first_round_matches), 2):                
                new_match = Match.objects.create(stage=current_stage)
                
                next_lose_match_set1 = False                
                next_lose_match_set2 = False                
                while not next_lose_match_set1 and not next_lose_match_set2:
                    if i >= len(upper_first_round_matches):
                        next_lose_match_set1 = True
                    elif not upper_first_round_matches[i].next_lose_match: 
                        upper_first_round_matches[i].next_lose_match = new_match
                        upper_first_round_matches[i].save()
                        next_lose_match_set1 = True
                    if i + 1 >= len(upper_first_round_matches):
                        next_lose_match_set2 = True
                    elif not upper_first_round_matches[i + 1].next_lose_match: 
                        upper_first_round_matches[i + 1].next_lose_match = new_match
                        upper_first_round_matches[i + 1].save()
                        next_lose_match_set2 = True
                    i += 2                 
                
                if count < len(additional_lower_matches):
                    additional_lower_matches[count].next_match = new_match
                    additional_lower_matches[count].save()
                if count+1 < len(additional_lower_matches):
                    additional_lower_matches[count+1].next_match = new_match
                    additional_lower_matches[count+1].save()
                count += 2
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
            
            for i, match in enumerate(upper_stage_losers_matches, start=0):
                new_match = Match.objects.create(stage=current_stage)
                match.next_lose_match = new_match
                match.save()
                if previous_lower_stage_matches_len > i:
                    previous_lower_stage_matches[i].next_match = new_match
                    previous_lower_stage_matches[i].save()
                i += 1

    # Финальный этап
    last_stage_position = TournamentStage.objects.filter(tournament=tournament).order_by("position").last().position
    final_stage = TournamentStage.objects.create(
        name="Финал", tournament=tournament, position=last_stage_position + 1
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
    first_stage_position = TournamentStage.objects.filter(tournament=tournament).order_by("position").first().position
    tournament.active_stage_position = first_stage_position
    tournament.save()


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
    
    stage_position_offset = tournament.get_stage_offset()

    for position in range(1, matches_count+1):
        stage_name = f"Этап {position}"
        stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=position + stage_position_offset)                    
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                Match.objects.create(
                    participant1=participants[i],
                    participant2=participants[j],
                    stage=stage
                )

def create_round_robin_bracket_2step(tournament):
    """Участники разделяются на N групп. В каждой группе проходит round robin этап. """
    groups_count = tournament.max_participants // tournament.participants_in_group
    splitted_participants = tournament.get_participants_for_groups(groups_count)
    position = 1
    group_number = 1
    for participants in splitted_participants:
        rounds_count = tournament.rounds_count if tournament.rounds_count else 1
        
        for _ in range(rounds_count):
            stage_name = f"Группа {group_number}. Этап {position}"
            stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=position)                    
            for i in range(len(participants)):
                for j in range(i + 1, len(participants)):
                    Match.objects.create(
                        participant1=participants[i],
                        participant2=participants[j],
                        stage=stage
                    )
            position += 1
        group_number += 1

def create_swiss_bracket(tournament, matches_data, participants:list):
    num_participants = len(participants)

    stage_position_offset = tournament.get_stage_offset() # Для Двуступенчатых турниров

    stage_name = "Этап 1"
    stage = TournamentStage.objects.create(name=stage_name, tournament=tournament, position=1 + stage_position_offset)

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
    stage_position_offset = tournament.get_stage_offset() # Для Двуступенчатых турниров

    # Каждый этап будет как событие(тур) турнира
    rounds_count = max(tournament.rounds_count, 1)
    for i in range(1, rounds_count+1):
        stage_name = f"Этап {i}"
        TournamentStage.objects.create(name=stage_name, tournament=tournament, position=i + stage_position_offset)            

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

def assign_final_positions(tournament):# TODO
    qualified_participants = []
    if tournament.tournament_type == 1:
        qualified_participants = Participant.objects.filter(tournament=tournament, qualified=True)
    not_qualified_participants = Participant.objects.filter(tournament=tournament, qualified=False)
    if tournament.check_score_difference_on_draw:
        if qualified_participants:
            qualified_participants = sorted(qualified_participants, key=lambda x: (x.score, x.get_score_difference()), reverse=True)
        not_qualified_participants = sorted(not_qualified_participants, key=lambda x: (x.score, x.get_score_difference()), reverse=True)

    else:
        if tournament.tournament_type == 0:
            if qualified_participants:
                qualified_participants = qualified_participants.order_by('-score')
            not_qualified_participants = not_qualified_participants.order_by('-score')
        else:
            if qualified_participants:
                qualified_participants = qualified_participants.order_by('-final_step_score')
            not_qualified_participants = not_qualified_participants.order_by('-final_step_score')

    for index, participant in enumerate(qualified_participants, start=1):
        participant.place = index
        participant.save()

    for index, participant in enumerate(not_qualified_participants, start=len(qualified_participants)+1):
        participant.place = index
        participant.save()

def assign_final_positions_leaderboard(tournament):
    stages = TournamentStage.objects.filter(tournament=tournament)

    participant_scores = {}
    for stage in stages:
        results = StageResult.objects.filter(stage=stage)
        for result in results:
            participant = result.participant
            participant_scores[participant] = participant_scores.get(participant, 0) + result.score

    sorted_participants = sorted(participant_scores.items(), key=lambda x: x[1], reverse=True)

    if tournament.tournament_type == 1:
        qualified_participants = [p for p, score in sorted_participants if p.qualified]
        not_qualified_participants = [p for p, score in sorted_participants if not p.qualified]
        sorted_participants = qualified_participants + not_qualified_participants
    else:
        sorted_participants = [p for p, score in sorted_participants]

    current_position = 1
    prev_score = None
    for participant in sorted_participants:
        if participant_scores[participant] != prev_score:
            participant.place = current_position
        prev_score = participant_scores[participant]
        participant.save()
        current_position += 1

def assign_final_positions_single_elimination(tournament:Tournament):
    stages = TournamentStage.objects.filter(tournament=tournament).order_by('-position')  # Получаем этапы в обратном порядке
    end = len(stages) - tournament.group_stages_count()
    count = 0
    for place, stage in enumerate(stages, start=1):
        if count == end and tournament.bracket == 1:
            break
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
        count += 1

def assign_final_positions_double_elimination(tournament):
    stages = TournamentStage.objects.filter(tournament=tournament).order_by('-position')
    end = len(stages) - tournament.group_stages_count()
    count = 0
    for place, stage in enumerate(stages, start=1):
        if count == end and tournament.tournament_type == 1:
            break
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
        count += 1

def assign_final_positions_group_stage(tournament):
    qualified_count = Participant.objects.filter(tournament=tournament, qualified=True).count()
    starting_position = qualified_count + 1

    non_qualified_participants = Participant.objects.filter(
        tournament=tournament, 
        qualified=False
    ).order_by('-score')

    for index, participant in enumerate(non_qualified_participants, start=starting_position):
        participant.place = index
        participant.save()

def save_stage_score(participant, stage, score):
    if participant:
        try:
            result = StageResult.objects.get(stage=stage, participant=participant)
            result.score = score 
            result.save()                               
        except:
            StageResult.objects.create(stage=stage, participant=participant, score=score)

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