class EmptyListError(Exception):
    """Список homework пуст."""

    pass


class IsNot200Error(Exception):
    """Ответ сервера не равен 200."""

    pass


class RequestError(Exception):
    """Ошибка запроса."""

    pass
