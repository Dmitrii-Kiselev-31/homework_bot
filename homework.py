import os
import sys
import time
import logging
from http import HTTPStatus
import requests
import telegram

from dotenv import load_dotenv
import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    logger.info('Начата отправка сообщения в телеграм')
    chat_id = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat_id, text=message)
    except telegram.error.Unauthorized as error:
        raise telegram.error.Unauthorized(
            f'Сообщение в Telegram не отправлено, ошибка авторизации {error}.'
        )
    except telegram.error.TelegramError as error:
        raise telegram.error.TelegramError(
            f'Сообщение в Telegram не отправлено {error}'
        )
    else:
        logging.info('Сooбщение успешно отправлено')


def get_api_answer(current_timestamp):
    """Делаем запрос к API сервису YP."""
    timestamp = current_timestamp or int(time.time())
    requests_params = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    try:
        logger.info('Начата проверка запроса к API сервису')
        response = requests.get(**requests_params)
    except exceptions.RequestError as err:
        logger.error(f'Ошибка при запросе к основному API:{err}')
        raise exceptions.RequestError(
            f'Ошибка при запросе к основному API:{err}'
        )
    if response.status_code != HTTPStatus.OK:
        raise requests.exceptions.RequestException(
            'Статус ответ сервера не равен 200!',
            response.status_code, response.text,
            response.headers, requests_params
        )
    return response.json()


def parse_status(homework):
    """Анализируем статус."""
    if homework is None:
        raise ValueError('список homework отсутствует')
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logger.error(f'Ошибка доступа по ключу {error}')
        raise KeyError('Неизвестный статус работы')


def check_response(response):
    """Проверяем ответ API."""
    logger.info('Проверка API на корректность началась')
    if not isinstance(response, dict):
        raise TypeError('Ответ API отличен от словаря')
    try:
        homeworks = response['homeworks']
    except KeyError as e:
        raise KeyError(
            f'Ошибка доступа по ключу homeworks или response: {e}'
        )
    if homeworks == 0:
        raise IndexError('Список домашних работ пуст')
    if not isinstance(homeworks, list):
        raise TypeError(
            'Данные не читаемы')
    if homeworks == []:
        raise exceptions.EmptyListError(
            'Обновлений пока что нет, ждем следующий запрос'
        )
    return homeworks


def check_tokens():
    """Проверка доступности токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    else:
        return False


def main():
    """Главная функция запуска бота."""
    logging.basicConfig(
        handlers=[
            logging.StreamHandler(), logging.FileHandler(
                filename="program.log", encoding='utf-8'
            )
        ],
        format='%(asctime)s, %(levelname)s, %(message)s,'
        ' %(name)s, %(funcName)s, %(module)s, %(lineno)d',
        level=logging.INFO)

    if not check_tokens():
        old_errors = ''
        logger.critical('Ошибка запуска бота: переменные отсутствуют')
        sys.exit('Выход из прогрмаммы: переменные отсутствуют')
    else:
        logger.info('Запуск бота')
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        current_name = ''
        current_timestamp: int = 1549962000
        prev_report = {
            'name_messages': current_name,
        }
        response = get_api_answer(current_timestamp)
        homeworks = check_response(response)
        current_report = {
            'name_messages': homeworks[0].get('homework_name'),
            'output': homeworks[0].get('data')
        }
        try:
            if current_report != prev_report:
                prev_report = current_report
                message = parse_status(homeworks[0])
                send_message(bot, message)
                prev_report = current_report.copy()
            else:
                logging.debug('Статус не изменился')
        except Exception as error:
            message = f'Сбой в работе функции main {error}'
            if old_errors != str(error):
                old_errors = str(error)
                send_message(bot, message)
            logger.critical(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':

    main()
