import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import datetime
import requests
from dateutil import parser as date_parser
import re
import os

# Import our database utilities
from db_utils import (
    ensure_user_exists, add_reminder, get_user_notes, add_note,
    get_user_settings, update_user_setting, add_conversation_context,
    check_database_health
)

# Command Handlers

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user = update.effective_user
    
    # Ensure user exists in database
    ensure_user_exists(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""
Hello {user.first_name}! 👋

I'm AlaX, your automated life assistant. Here's what I can help you with:

📝 /remind - Set reminders for important tasks
🌤️ /weather - Get weather information
📄 /note - Save and manage your notes  
⚙️ /settings - Configure your preferences

You can also just chat with me naturally, and I'll do my best to help!
    """
    
    await update.message.reply_text(welcome_text)

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /remind command"""
    user_id = update.effective_user.id
    ensure_user_exists(user_id)
    
    # Check if user provided reminder text
    if not context.args:
        await update.message.reply_text(
            "Please provide a reminder message.\n\n"
            "Examples:\n"
            "• `/remind Buy groceries in 2 hours`\n"
            "• `/remind Call mom at 3pm tomorrow`\n"
            "• `/remind Meeting at 2024-03-15 10:30`"
        )
        return
    
    reminder_text = ' '.join(context.args)
    
    # Parse time from the reminder text
    parsed_time = parse_time_from_text(reminder_text)
    
    if parsed_time:
        # Save to database using utility function
        reminder_id = add_reminder(user_id, reminder_text, parsed_time)
        
        await update.message.reply_text(
            f"✅ Reminder set!\n"
            f"📝 {reminder_text}\n"
            f"⏰ {parsed_time.strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        await update.message.reply_text(
            "I couldn't understand the time. Please try:\n"
            "• 'in X minutes/hours/days'\n"
            "• 'at 3pm tomorrow'\n"
            "• 'on 2024-03-15 at 10:30'"
        )

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /weather command"""
    user_id = update.effective_user.id
    ensure_user_exists(user_id)
    
    # Get user's saved location from settings
    settings = get_user_settings(user_id)
    
    location = None
    if context.args:
        location = ' '.join(context.args)
    elif settings and settings['weather_location']:
        location = settings['weather_location']
    else:
        await update.message.reply_text(
            "Please provide a location:\n"
            "`/weather New York`\n\n"
            "Or set a default location in /settings"
        )
        return
    
    # Get weather data (you'll need an API key from OpenWeatherMap)
    weather_data = get_weather(location)
    
    if weather_data:
        weather_text = format_weather_message(weather_data)
        await update.message.reply_text(weather_text)
    else:
        await update.message.reply_text(
            f"Sorry, I couldn't get weather data for '{location}'. "
            "Please check the location name and try again."
        )

async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /note command"""
    user_id = update.effective_user.id
    
    if not context.args:
        # Show recent notes
        conn = sqlite3.connect('alax.db')
        cursor = conn.cursor()
        cursor.execute(
            'SELECT content, created_at FROM notes WHERE user_id = ? ORDER BY created_at DESC LIMIT 5',
            (user_id,)
        )
        notes = cursor.fetchall()
        conn.close()
        
        if notes:
            notes_text = "📝 Your recent notes:\n\n"
            for i, (content, created_at) in enumerate(notes, 1):
                date = datetime.datetime.fromisoformat(created_at).strftime('%m/%d %H:%M')
                notes_text += f"{i}. {content[:50]}{'...' if len(content) > 50 else ''}\n   📅 {date}\n\n"
            
            # Add inline keyboard for note management
            keyboard = [
                [InlineKeyboardButton("🔍 Search Notes", callback_data="search_notes")],
                [InlineKeyboardButton("🗑️ Delete Note", callback_data="delete_note")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(notes_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text("You don't have any notes yet. Use `/note <your note>` to create one!")
        return
    
    # Save new note
    note_content = ' '.join(context.args)
    
    conn = sqlite3.connect('alax.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO notes (user_id, content) VALUES (?, ?)',
        (user_id, note_content)
    )
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"📝 Note saved!\n\n{note_content}\n\n"
        "Use `/note` without text to see all your notes."
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /settings command"""
    user_id = update.effective_user.id
    
    # Create inline keyboard for settings
    keyboard = [
        [InlineKeyboardButton("🌍 Set Location", callback_data="set_location")],
        [InlineKeyboardButton("⏰ Set Timezone", callback_data="set_timezone")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="toggle_notifications")],
        [InlineKeyboardButton("📊 View Settings", callback_data="view_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ Settings Menu\n\nChoose what you'd like to configure:",
        reply_markup=reply_markup
    )

# Callback handler for inline keyboard buttons
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "view_settings":
        # Show current settings
        conn = sqlite3.connect('alax.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM user_settings WHERE user_id = ?', (user_id,))
        settings = cursor.fetchone()
        conn.close()
        
        if settings:
            settings_text = f"""
⚙️ Your Current Settings:

🌍 Location: {settings[2] or 'Not set'}
⏰ Timezone: {settings[1]}
🔔 Notifications: {'Enabled' if settings[3] else 'Disabled'}
            """
        else:
            settings_text = "⚙️ No settings configured yet."
        
        await query.edit_message_text(settings_text)
    
    # Handle other callback data...
    elif query.data == "set_location":
        await query.edit_message_text(
            "🌍 Please send me your default location for weather updates.\n\n"
            "Example: New York, NY or London, UK"
        )
        # Set a flag to expect location input next
        context.user_data['expecting'] = 'location'

# Utility functions

def parse_time_from_text(text):
    """Parse time expressions from natural language"""
    now = datetime.datetime.now()
    
    # Simple regex patterns for time parsing
    patterns = {
        r'in (\d+) minutes?': lambda m: now + datetime.timedelta(minutes=int(m.group(1))),
        r'in (\d+) hours?': lambda m: now + datetime.timedelta(hours=int(m.group(1))),
        r'in (\d+) days?': lambda m: now + datetime.timedelta(days=int(m.group(1))),
        r'at (\d{1,2}):(\d{2})': lambda m: now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0),
        r'tomorrow at (\d{1,2}):(\d{2})': lambda m: (now + datetime.timedelta(days=1)).replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    }
    
    for pattern, func in patterns.items():
        match = re.search(pattern, text.lower())
        if match:
            return func(match)
    
    # Try parsing ISO format dates
    try:
        return date_parser.parse(text)
    except:
        return None

def get_weather(location):
    """Get weather data from OpenWeatherMap API"""
    # You'll need to get a free API key from openweathermap.org
    API_KEY = "YOUR_OPENWEATHER_API_KEY"
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={API_KEY}&units=metric"
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def format_weather_message(weather_data):
    """Format weather data into a readable message"""
    try:
        temp = weather_data['main']['temp']
        feels_like = weather_data['main']['feels_like']
        description = weather_data['weather'][0]['description'].title()
        humidity = weather_data['main']['humidity']
        location = weather_data['name']
        
        return f"""
🌤️ Weather for {location}

🌡️ Temperature: {temp}°C (feels like {feels_like}°C)
📝 Conditions: {description}
💧 Humidity: {humidity}%
        """
    except:
        return "Sorry, I couldn't format the weather data."

# Main application setup
def main():
    bot = os.getenv('token')
    # Create the Application
    application = Application.builder().token(bot).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("note", note_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Add callback handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()