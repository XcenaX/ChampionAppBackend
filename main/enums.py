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

def get_list_from_tuple(choice_tuples):
    return [item[1] for item in choice_tuples]