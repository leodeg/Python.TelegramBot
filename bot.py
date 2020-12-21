import config
import logging
import requests
import json
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Логгирование
logging.basicConfig(format='%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', context.bot, update.error)


def start_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text='Привет, давай пообщаемся?')


def echo_message(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


def help_command(update, context):
    response = 'Комманды: ' \
               '\n/start - запустить бота ' \
               '\n/help - доступные комманды ' \
               '\n/weather (название города) - текущая погода'
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def text_message(update, context):
    response = 'Получил Ваше сообщение: ' + update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id, text=response)


def weather_command(update, context):
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Введите название города!')
    else:
        city = context.args[0]
        request_to_openweather = requests.post(
            url = config.api_url_openweather,
            params ={
                'q':city,
                'appid':config.token_openweather,
                'units':'metric',
                'lang':'ru'
            }
        )

        result = ''
        if request_to_openweather.status_code == 200:
            result = get_weather_message(request_to_openweather)
        else:
            result = 'Не удалось найти погоду для данного города: ' + city + '. Проверьте, правильно ли введенны данные.'

        context.bot.send_message(chat_id=update.effective_chat.id, text=result)


def weather_by_location_command(update, context):
    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message

    location_lat = message.location.latitude
    location_lon = message.location.longitude

    request_to_openweather = requests.post(
        url=config.api_url_openweather,
        params={
            'lat': location_lat,
            'lon': location_lon,
            'appid': config.token_openweather,
            'units': 'metric',
            'lang': 'ru'
        }
    )

    result = ''
    if request_to_openweather.status_code == 200:
        result = get_weather_message(request_to_openweather)
    else:
        result = f'Не удалось найти погоду для данных координат: ({location_lat}, {location_lon}).'

    context.bot.send_message(chat_id=update.effective_chat.id, text=result)


def get_weather_message(request):
    response = json.loads(request.content)
    city = response['name']
    temperature = response['main']['temp']
    min_temperature = response['main']['temp_min']
    max_temperature = response['main']['temp_max']
    pressure = response['main']['pressure']
    description = response['weather'][0]['description']
    return f'В городе {city} {description}, текущая температура - {temperature}, минимальная температура - ' \
             f'{min_temperature}, максимальная температура - {max_temperature}, давление - {pressure}.'


def main():
    # Диспетчер телеграмма
    updater = Updater(token=config.token_telegram)  # Токен API к Telegram
    dispatcher = updater.dispatcher

    # Хендлеры
    start_command_handler = CommandHandler('start', start_command)
    help_command_handler = CommandHandler('help', help_command)
    weather_command_handler = CommandHandler('weather', weather_command, pass_args=True)

    # text_message_handler = MessageHandler(Filters.text, echo_message)
    text_message_handler = MessageHandler(Filters.text, text_message)
    weather_by_location_message_handler = MessageHandler(Filters.location,
                                                         weather_by_location_command,
                                                         pass_user_data=True)

    # Добавляем хендлеры в диспетчер
    dispatcher.add_handler(start_command_handler)
    dispatcher.add_handler(help_command_handler)
    dispatcher.add_handler(weather_command_handler)

    dispatcher.add_handler(text_message_handler)
    dispatcher.add_handler(weather_by_location_message_handler)

    dispatcher.add_error_handler(error)

    # Начинаем поиск обновлений
    updater.start_polling(clean=True)

    # Останавливаем бота, если были нажаты Ctrl + C
    updater.idle()


if __name__ == '__main__':
    main()
