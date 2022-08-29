import os


class IsNot200Error(Exception):
    """Ответ соединения сервера, не равен 200."""


class EmptyListError(Exception):
    """Список или словарь пуст."""


class UndocumentedStatusError(Exception):
    """Недокументированный статус домашней работы."""


class RequestError(Exception):
    """Ошибка запроса."""
