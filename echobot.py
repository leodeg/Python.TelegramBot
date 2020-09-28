import config
import telebot 

bot = telebot.TeleBot(config.token);

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.send_message(message, "Howdy, how are you doing?")

@bot.message_handler(func=lambda m: True)
def echo_all(message):
	bot.send_message(message, message.text)
    
if __name__ == '__main__':
    bot.polling(none_stop=True)