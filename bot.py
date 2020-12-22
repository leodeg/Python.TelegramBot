import config
import logging
import requests
import json
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import speech_recognition
import ftransc.core

# Логгирование
logging.basicConfig(format='%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"'.format(context.bot, context.error))


def start_command(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Привет, давай пообщаемся? Данный бот умеет показывать текущую погоду '
                                  'по команде /weather ( название города) или геолокации, а также распознавать голос.'
                             )


def echo_message(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


def help_command(update, context):
    response = 'Комманды: ' \
               '\n/start - запустить бота ' \
               '\n/help - доступные комманды ' \
               '\n/weather (название города) - текущая погода. ' \
               '\nУзнать погоду также можно по геолокации.'

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
            url=config.api_url_openweather,
            params={
                'q': city,
                'appid': config.token_openweather,
                'units': 'metric',
                'lang': 'ru'
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


def transcribe_voice_message(update, context):
    duration = update.message.voice.duration
    logger.info('transcribe_voice. Message duration: {}'.format(duration))

    # Конвертация аудио из [audio/x-opus+ogg] в [audio/x-wav]
    voice = context.bot.getFile(update.message.voice.file_id)
    audio = voice.download('file.oga')
    ftransc.core.transcode(audio, 'wav')

    # Получение голоса из аудиофайла
    recognizer = speech_recognition.Recognizer()
    with speech_recognition.WavFile('file.wav') as source:
        # recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.record(source)

    # Конвертация звука в текст
    text = ''
    try:
        text = recognizer.recognize_google(audio)
        logger.info(text)
    except speech_recognition.UnknownValueError:
        logger.warning('Невозможно распознать голос и конвертировать его в текст!')
    except speech_recognition.RequestError as error:
        logger.warning('Невозможно отправить запрос на распознание голоса! \nСообщение ошибки: [{}]'.format(error))

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


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
    transcribe_voice_message_handler = MessageHandler(Filters.voice, transcribe_voice_message)

    # Добавляем хендлеры в диспетчер
    dispatcher.add_handler(start_command_handler)
    dispatcher.add_handler(help_command_handler)
    dispatcher.add_handler(weather_command_handler)

    dispatcher.add_handler(text_message_handler)
    dispatcher.add_handler(weather_by_location_message_handler)
    dispatcher.add_handler(transcribe_voice_message_handler)

    dispatcher.add_error_handler(error)

    PORT = int(os.environ.get('PORT', 5000))

    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=config.token_telegram)

    updater.bot.setWebhook('https://leodegtelegrambot.herokuapp.com/' + config.token_telegram)

    # Начинаем поиск обновлений
    #updater.start_polling(clean=True)

    # Останавливаем бота, если были нажаты Ctrl + C
    updater.idle()


if __name__ == '__main__':
    main()
