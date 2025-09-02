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
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=message.text,
            config=types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0))
        )
        
        if response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "Sorry, I couldn't generate a response.")
            
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Sorry, there was an error processing your request.")

bot.infinity_polling()