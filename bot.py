import config
import logging
import requests
import json
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import speech_recognition
import bs4
import subprocess

# Логгирование
logging.basicConfig(format='%(asctime)s --- %(name)s --- %(levelname)s --- %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def start_command(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Привет, давай пообщаемся? '
             '\nБот умеет переводить голосовые сообщения на русском языке.'
             '\nБот умеет показывать текущую погоду по команде - /weather (название города) или вашей геолокации.'
             '\nБот умеет производить поиск в Google по команде - /google (запрос). '
             '\nБот умеет поизводить поиск по сайту Хабр - /habr (запрос).'
             '\nВсе запросы пишутся без скобочек, просто через пробел.'
    )


def echo_message(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


def help_command(update, context):
    response = 'Комманды: ' \
               '\n/start - запустить бота' \
               '\n/help - доступные комманды' \
               '\n/weather (название города) - текущая погода. Узнать погоду можно по геолокации.' \
               '\n/google (запрос) - поиск запроса в google ' \
               '\n/habr (запрос) - поиск по хабру'

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
    voice = context.bot.getFile(update.message.voice.file_id)
    voice.download('audio.ogg')

    # Конвертация "ogg" в "wav"
    subprocess.run(['ffmpeg', '-i', 'audio.ogg', 'audio.wav', '-y'])

    # Получение голоса из аудиофайла
    recognizer = speech_recognition.Recognizer()
    with speech_recognition.WavFile('audio.wav') as source:
        audio = recognizer.record(source)

    # Конвертация звука в текст
    try:
        text = recognizer.recognize_google(audio, language='ru_RU')
        logger.info(text)
    except speech_recognition.UnknownValueError:
        text = 'Невозможно распознать голос и конвертировать его в текст!'
        logger.warning(text)
    except speech_recognition.RequestError as error:
        text = 'Невозможно отправить запрос на распознание голоса! \nСообщение ошибки: [{}]'.format(error)
        logger.warning(text)

    context.bot.send_message(chat_id=update.effective_chat.id, text=text)


def google_search_command(update, context):
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Введите поисковый запрос!')
    else:
        search_query = ' '.join(context.args[0:])
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Ваш запрос: {}'.format(search_query))

        result = requests.get('https://google.com/search?q={}'.format(search_query))
        result.raise_for_status()

        soup = bs4.BeautifulSoup(result.text, "html.parser")
        result_div = soup.find_all('div', attrs={'class': 'ZINbbc'})

        links = []
        titles = []
        descriptions = []
        for r in result_div:
            # Checks if each element is present, else, raise exception
            try:
                link = r.find('a', href=True)
                title = r.find('div', attrs={'class': 'vvjwJb'}).get_text()
                description = r.find('div', attrs={'class': 's3v9rd'}).get_text()

                # Check to make sure everything is present before appending
                if link != '' and title != '' and description != '':
                    links.append(link['href'])
                    titles.append(title)
                    descriptions.append(description)
            # Next loop if one element is not present
            except:
                continue

        for i in range(len(links)):
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text='https://google.com' + links[i])


def habr_search_command(update, context):
    if len(context.args) == 0:
        context.bot.send_message(chat_id=update.effective_chat.id, text='Введите поисковый запрос!')
    else:
        search_query = ' '.join(context.args[0:])
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Ваш запрос: {}'.format(search_query))

        result = requests.get('https://habr.com/ru/search/?q={}'.format(search_query))
        result.raise_for_status()

        soup = bs4.BeautifulSoup(result.text, "html.parser")
        result = soup.find_all('h2', attrs={'class': 'post__title'})

        links = []
        for r in result:
            link = r.find('a', href=True)
            if link != '':
                links.append(link['href'])

        links_count = len(links)
        if links_count > 0:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Количество найденных статей: {}'.format(links_count))
            for i in range(links_count):
                context.bot.send_message(chat_id=update.effective_chat.id, text=links[i])
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Статей по запросу [{}] не найдено!'.format(search_query))


def main():
    # Диспетчер телеграмма
    updater = Updater(token=config.token_telegram, use_context=True)  # Токен API к Telegram
    dispatcher = updater.dispatcher

    # Хендлеры
    start_command_handler = CommandHandler('start', start_command)
    help_command_handler = CommandHandler('help', help_command)
    weather_command_handler = CommandHandler('weather', weather_command, pass_args=True)
    google_search_command_handler = CommandHandler('google', google_search_command, pass_args=True)
    habr_search_command_handler = CommandHandler('habr', habr_search_command, pass_args=True)

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
    dispatcher.add_handler(google_search_command_handler)
    dispatcher.add_handler(habr_search_command_handler)

    dispatcher.add_handler(text_message_handler)
    dispatcher.add_handler(weather_by_location_message_handler)
    dispatcher.add_handler(transcribe_voice_message_handler)

    # dispatcher.add_error_handler(error)

    PORT = int(os.environ.get('PORT', 5000))

    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=config.token_telegram)
    updater.bot.setWebhook('https://leodegtelegrambot.herokuapp.com/' + config.token_telegram)

    # Начинаем поиск обновлений
    # updater.start_polling(clean=True)

    # Останавливаем бота, если были нажаты Ctrl + C
    updater.idle()


if __name__ == '__main__':
    main()
