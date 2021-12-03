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

coupons_url = "https://couponscorpion.com/"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = os.environ.get("NOTIFICATIONS_BOT_TOKEN")

updater = Updater(TOKEN, use_context=True)


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

def stop(update, context):
    """Stop the bot."""
    update.message.reply_text('Deleting all of your alerts! bye!')
    chat_id = update.message.chat_id
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    db.alerts.delete_many({"chat_id": chat_id})
    

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
    try:
        chat_id = update.message.chat_id
        movie_name, year = get_movie_info(update.message.text.replace("/moviealert ", ""))
        movie_name1 = movie_name.replace(":", "")
        movie_name1 = movie_name1.replace(" ", "-").lower() + "-" + str(year)
        movie_link = f"https://yts.mx/movies/{movie_name1}"
        to_db(chat_id, movie_name, movie_link)
        update.message.reply_text("You will be notified when " + movie_name + " is released!")
    except Exception as e:
        print(e)
        update.message.reply_text("invalid URL. Try something like this: /moviealert https://imdb.com/title/tt0111161/")

def remove_from_db(url, chat_id):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    db.alerts.delete_many({"chat_id": chat_id, "movie_link": url})

def alert_list(update, context):
    try:
        chat_id = update.message.chat_id
        ca = certifi.where()
        client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
        db = client.movie_alerts
        alerts = db.alerts.find({"chat_id": chat_id})
        index = 1
        message = ""
        for alert in alerts:
            message += str(index) + ". " + alert["movie_name"] + "\n"
            index += 1
        if message != "":
            update.message.reply_text(message)
        else:
            update.message.reply_text("You have no alerts!")
    except Exception as e:
        print(e)
        update.message.reply_text("Something went wrong!")

def delete_alert(update: Update, context: CallbackContext):
    try:
        chat_id = update.message.chat_id
        movie_name, year = get_movie_info(update.message.text.replace("/deletealert ", ""))
        movie_name1 = movie_name.replace(":", "")
        movie_name1 = movie_name1.replace(" ", "-").lower() + "-" + str(year)
        movie_link = f"https://yts.mx/movies/{movie_name1}"
        remove_from_db(movie_link, chat_id)
        update.message.reply_text(movie_name + " is removed from the movie alert list!")
    except Exception as e:
        print(e)
        update.message.reply_text("invalid URL. Try something like this: /moviealert https://imdb.com/title/tt0111161/")

def to_db(chat_id, movie_name, movie_link):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    db.alerts.insert_one({"chat_id": chat_id, "movie_name": movie_name, "movie_link": movie_link})

def check_movies():
    print("in")
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    movies = db.alerts.find()
    for movie in movies:
        movie_link = movie['movie_link']
        r = requests.get(movie_link, headers={'User-Agent': 'Mozilla/5.0'}).text
        soup = BeautifulSoup(r, 'html.parser')
        print(soup.title.string)
        if "Page not found (Error 404)" not in soup.title.string:
            db.alerts.delete_one({"_id": movie['_id']})
            movie_name = movie['movie_name']
            chat_id = movie['chat_id']
            updater.bot.send_message(chat_id, "Hey! " + movie_name + " is out! Check it out here: " + movie_link)
            updater.bot.send_message(chat_id, "Also I removed the movie from the movie alert list!")

def register_coupons(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    db.registered.insert_one({"_id": update.message.chat_id})
    update.message.reply_text("You are now registered for coupons alerts!")

def unregister_coupons(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    db.registered.delete_one({"_id": update.message.chat_id})
    update.message.reply_text("You are now unregistered for coupons alerts!")

def get_coupons():
    ##"""Get the coupons from the website."""
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
        soup = BeautifulSoup(response, "html.parser")
        list_of_coupons = soup.find("div", {"class": "eq_grid pt5 rh-flex-eq-height col_wrap_three"})
        articles = list_of_coupons.find_all("article")
        first_name = articles[0].find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
        first_coupon_url = first_name.find("a")["href"]
        new_coupons, last_url = connect_to_db_coupons(first_coupon_url, True)
        if new_coupons:
            hit = False
            for article in articles:
                try:
                    name = article.find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
                    coupon_url = name.find("a")["href"]
                    if coupon_url == last_url:
                        hit = True
                        break
                    percent = article.find("span", {"class": "grid_onsale"}).text
                    if "100%" not in percent:
                        continue
                    image = article.find("img", {"class": "ezlazyload"})["data-ezsrc"]
                    time.sleep(3)
                    send_coupons(name.text, percent, coupon_url, image)
                except Exception as e:
                    print(e)
                    print("False coupon found")
            if not hit:
                index = 2
                while not hit:
                    page_url = url + f"page/{index}/"
                    response = requests.get(page_url, headers={'User-Agent': 'Mozilla/5.0'}).text
                    soup = BeautifulSoup(response, "html.parser")
                    list_of_coupons = soup.find("div", {"class": "eq_grid pt5 rh-flex-eq-height col_wrap_three"})
                    articles = list_of_coupons.find_all("article")
                    first_name = articles[0].find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
                    coupon_url = first_name.find("a")["href"]
                    if coupon_url == last_url:
                        hit = True
                        break
                    for article in articles:
                        try:
                            name = article.find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
                            coupon_url = name.find("a")["href"]
                            if coupon_url == last_url:
                                hit = True
                                break
                            percent = article.find("span", {"class": "grid_onsale"}).text
                            if "100%" not in percent:
                                continue
                            image = article.find("img", {"class": "ezlazyload"})["data-ezsrc"]
                            time.sleep(3)
                            send_message(name.text, percent, coupon_url, image)
                        except Exception as e:
                            print(e)
                            print("False coupon found")
                    index += 1
            connect_to_db_coupons(first_coupon_url, False)
    except Exception as e:
        print(e)

def connect_to_db_coupons(url, read):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    if not read:
        query = {"_id" : 1 }
        db.coupons.replace_one(query ,{"url": url, "_id" : 1})
    else:
        last_url = db.coupons.find_one({"_id": 1})["url"]
        if last_url == url:
            print("No new coupons found")
            return [False, last_url]
        return [True, last_url]

def send_coupons(name, percent, coupon_url, image):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    chat_ids = db.registered.find()
    for chat_id in chat_ids:
        updater.dispatcher.bot.sendPhoto(chat_id=chat_id["_id"], photo=image, caption=f'{name} is {percent}: {coupon_url}')


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary


    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("moviealert", movie_alert))
    dp.add_handler(CommandHandler("stop", stop))
    dp.add_handler(CommandHandler("deletealert", delete_alert))
    dp.add_handler(CommandHandler("alertlist", alert_list))
    dp.add_handler(CommandHandler("coupons", register_coupons))
    dp.add_handler(CommandHandler("unregistercoupons", unregister_coupons))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN,
                      webhook_url="https://my-notifications-bot.herokuapp.com/" + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()