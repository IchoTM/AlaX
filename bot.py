from dotenv import load_dotenv
from os import getenv
from telebot import TeleBot

load_dotenv()

bot = TeleBot(getenv('token'))

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Hello, I am AlaX. A general purpose virtual assistant. How can I help you?")

bot.infinity_polling()