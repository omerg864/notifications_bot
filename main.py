from bs4 import BeautifulSoup
import requests
from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import os
import signal
import pymongo
import certifi
import time

DEBUG = os.environ.get("DEBUG_VALUE") == "True"
PORT = int(os.environ.get('PORT', 8443))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = os.environ.get("NOTIFICATIONS_BOT_TOKEN")


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def get_movie_info(url):
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
    soup = BeautifulSoup(r, 'html.parser')
    movie_name = soup.find('h1', {'class': 'TitleHeader__TitleText-sc-1wu6n3d-0 cLNRlG'}).text
    year = int(soup.find_all('a', {'class': 'ipc-link ipc-link--baseAlt ipc-link--inherit-color TitleBlockMetaData__StyledTextLink-sc-12ein40-1 rgaOW'})[0].text)
    return [movie_name, year]

def movie_alert(update: Update, context: CallbackContext):
    """
    This function will be called when the user sends a message to the bot.
    """
    chat_id = update.message.chat_id
    print(chat_id)
    movie_name, year = get_movie_info(update.message.text.replace("/moviealert ", ""))
    movie_name1 = movie_name.replace(":", "")
    movie_name1 = movie_name1.replace(" ", "-") + "-" + str(year)
    movie_link = f"https://yts.mx/movies/{movie_name1}"
    to_db(chat_id, movie_name, movie_link)
    update.message.reply_text("You will be notified when " + movie_name + " is released!")

def to_db(chat_id, movie_name, movie_link):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    db.alerts.insert_one({"chat_id": chat_id, "movie_name": movie_name, "movie_link": movie_link})

def check_movies(updater):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    movies = db.alerts.find()
    print(movies)
    for movie in movies:
        movie_link = movie['movie_link']
        r = requests.get(movie_link, headers={'User-Agent': 'Mozilla/5.0'}).text
        soup = BeautifulSoup(r, 'html.parser')
        if "Page not found (Error 404)" not in soup.title.string:
            db.alerts.delete_one({"_id": movie['_id']})
            movie_name = movie['movie_name']
            chat_id = movie['chat_id']
            updater.bot.send_message(chat_id, "Hey! " + movie_name + " is out! Check it out here: " + movie_link)
            updater.bot.send_message(chat_id, "Also I removed the movie from the movie alert list!")


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary

    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("moviealert", movie_alert))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN,
                      webhook_url="https://my-notifications-bot.herokuapp.com/" + TOKEN)
    
    check_movies(updater)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()