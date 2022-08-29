import datetime
import json
import logging
import os
import time

import requests
import telegram
from exceptions import (IsNot200Error,
    EmptyListError,
    UndocumentedStatusError,
    RequestError
)
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s, %(name)s,%(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            f'Сообщение в Telegram отправлено: {message}')
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение в Telegram не отправлено: {telegram_error}')


def get_api_answer(url, current_timestamp):
    """Делаем запрос к API сервису."""
    current_timestamp = current_timestamp or int(time.time())
    headers = HEADERS
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
        if response.status_code != 200:
            code_api_msg = (
                f'Эндпоинт {url} недоступен.'
                f' Код ответа API: {response.status_code}')
            logger.error(code_api_msg)
            raise IsNot200Error(code_api_msg)
        return response.json()
    except requests.exceptions.RequestException as request_error:
        code_api_msg = f'Код ответа API (RequestException): {request_error}'
        logger.error(code_api_msg)
        raise RequestError(code_api_msg) from request_error
    except json.JSONDecodeError as value_error:
        code_api_msg = f'Код ответа API (ValueError): {value_error}'
        logger.error(code_api_msg)
        raise json.JSONDecodeError(code_api_msg) from value_error


def parse_status(homework):
    """Анализируем статус."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except TypeError as error:
        mess = f'Ошибка {error} в получении информации, Список работ пуст'
        logging.error(mess)
        return mess


def check_response(response):
    """Проверяем ответ API."""
    if response.get('homeworks') is None:
        code_api_msg = (
            'Ошибка ключа homeworks или response'
            'имеет неправильное значение.')
        logger.error(code_api_msg)
        raise EmptyListError(code_api_msg)
    if response['homeworks'] == []:
        return {}
    status = response['homeworks'][0].get('status')
    if status not in HOMEWORK_STATUSES:
        code_api_msg = f'Ошибка недокументированный статус: {status}'
        logger.error(code_api_msg)
        raise UndocumentedStatusError(code_api_msg)
    return response['homeworks'][0]


def check_tokens():
    """Проверка доступности токенов."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    now = datetime.datetime.now()
    send_message(
        bot,
        f'Я начал свою работу: {now.strftime("%d-%m-%Y %H:%M")}')
    current_timestamp = 1
    tmp_status = 'reviewing'
    errors = True
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            if homework and tmp_status != homework['status']:
                message = parse_status(homework)
                send_message(bot, message)
                tmp_status = homework['status']
            logger.info(
                'Изменений нет, ждем 10 минут и проверяем API')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = False
                send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
