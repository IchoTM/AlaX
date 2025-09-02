from dotenv import load_dotenv
from os import getenv
from telebot import TeleBot
from google import genai
from google.genai import types

load_dotenv()

bot = TeleBot(getenv('token'))
client = genai.Client()

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "Hello, I am AlaX. A general purpose virtual assistant. How can I help you?")

@bot.message_handler(func=lambda msg: True)
def reply(message):
    reply = client.models.generate_content(
        model="gemini-2.5-flash",
        contents= message.text,
        config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0))
        )
    
    bot.reply_to(message, reply.text)

bot.infinity_polling()