from datetime import timedelta


TOURNAMENT_BRACKET_TYPE = (
    (0, 'Signle Elimination'),
    (1, 'Double Elimination'),
    (2, 'Round Robin'),
    (3, 'Swiss'),
    (4, 'Leaderboard'),
)

TOURNAMENT_TYPE = (
    (0, 'Одноступенчатый'),
    (1, 'Двуступенчатый'),
)

MATCH_STATUS = (
    (0, 'Запланирован'),
    (1, 'В процессе'),
    (2, 'Завершен'),
)

AMATEUR_MATCH_STATUS = (
    (0, 'Запланирован'),
    (1, 'В процессе'),
    (2, 'Завершен'),
    (3, 'Отменен'),
)

MATCH_RESULT = (
    (0, 'Победа'),
    (1, 'Поражение'),
    (2, 'Ничья'),
)

ROLE_CHOICES = (
    (0, 'Пользователь'),
    (1, 'Тренер'),
    (2, 'Продавец'),
    (3, 'Админ'),
)

DEGREE_CHOICES = (
    (0, 'Любитель'),
    (1, 'Профессионал'),
)

REGISTER_OPEN_UNTIL = (
    ('15 мин', timedelta(minutes=15)),
    ('30 мин', timedelta(minutes=30)),
    ('1 час', timedelta(hours=1)),
    ('2 часа', timedelta(hours=2)),
    ('6 часов', timedelta(hours=6)),
    ('1 день', timedelta(days=1)),
    ('2 дня', timedelta(days=2)),
)

def get_list_from_tuple(choice_tuples):
    return [item[1] for item in choice_tuples]