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
from PyPDF2 import PdfFileReader
import io

DEBUG = os.environ.get("DEBUG_VALUE") == "True"
PORT = int(os.environ.get('PORT', 8443))

coupons_url = "https://couponscorpion.com/"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = os.environ.get("NOTIFICATIONS_BOT_TOKEN")

updater = Updater(TOKEN, use_context=True)

commands = ["moviealert - following imdb url to add to your movie alert list", "deletealert - following imdb url to delete from your movie alert list",
            "alertlist - list of your movie alerts", "clearmoviealerts - delete all of your movie alerts", f"coupons - register to receive Udemy 100% off coupons",
            "unregistercoupons - unregister from receiving Udemy coupons", "stopbot - stop the bot and deletes your alert list"]


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi! check out the commands with /help')

def help(update, context):
    """Send a message when the command /help is issued."""
    message = ""
    index = 1
    for command in commands:
        message += str(index) + ". " + command + "\n"
        index += 1
    if message != "":
        update.message.reply_text(message)
    else:
        update.message.reply_text("Can't help you! good luck!")

def command_list(update, context):
    message = ""
    for command in commands:
        message += command + "\n"
    if message != "":
        update.message.reply_text(message)
    else:
        update.message.reply_text("Can't help you! good luck!")


def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def stop_bot(update, context):
    """Stop the bot."""
    update.message.reply_text('Deleting all of your alerts and stopping the bot! bye!')
    chat_id = update.message.chat_id
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    db.alerts.delete_many({"chat_id": chat_id})
    db = client.new_database
    db.registered.delete_many({"_id" : chat_id})
    

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

def clear_movie_alerts(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    chat_id = update.message.chat_id
    db.alerts.delete_many({"chat_id": chat_id})

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
            updater.dispatcher.bot.send_message(chat_id, "Hey! " + movie_name + " is out! Check it out here: " + movie_link)
            updater.dispatcher.bot.send_message(chat_id, "Also I removed the movie from the movie alert list!")

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
        response = requests.get(coupons_url, headers={'User-Agent': 'Mozilla/5.0'}).text
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
                    print(coupon_url)
                    print(last_url)
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
                count = 0
                while not hit:
                    page_url = coupons_url + f"page/{index}/"
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
                            send_coupons(name.text, percent, coupon_url, image)
                        except Exception as e:
                            print(e)
                            print("False coupon found")
                    index += 1
                    count += 1
                    if count == 50:
                        break
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

def get_fuel_settings():
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    fuel_settings = db.settings.find_one({"_id": 1})
    return fuel_settings["month"], fuel_settings["year"]

def get_data_from_gov():
    months = ["jan", "feb", "march", "april", "may", "june", "july", "august", "sep", "october", "nov", "dec"]
    months_full = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    gov_url = "https://www.gov.il/BlobFolder/news/fuel_{month}_{year}/he/fuel_{index}_{year}.pdf"
    gov_alt_url = "https://www.gov.il/BlobFolder/news/fuel_{month}_{year}/he/{index}_{year}.pdf"
    month, year = get_fuel_settings()
    try:
        print(gov_url.format(month=months[month], year=f"{year}", index=f"{month + 1}"))
        response = requests.get(gov_url.format(month=months[month], year=f"{year}", index=f"{month + 1}"))
        if "<title>error page</title>" not in response.text:
            get_from_pdf(response, month, year)
        else:
            print(gov_url.format(month=months[month], year=f"{year}", index=f"{months[month]}"))
            response = requests.get(gov_url.format(month=months[month], year=f"{year}", index=f"{months[month]}"))
            if "<title>error page</title>" not in response.text:
                get_from_pdf(response, month, year)
            else:
                print(gov_alt_url.format(month=months[month], year=f"{year}", index=f"{month + 1}"))
                response = requests.get(gov_alt_url.format(month=months[month], year=f"{year}", index=f"{month + 1}"))
                if "<title>error page</title>" not in response.text:
                    get_from_pdf(response, month, year)
                else:
                    print(gov_alt_url.format(month=months[month], year=f"{year}", index=f"{months[month]}"))
                    response = requests.get(
                        gov_alt_url.format(month=months[month], year=f"{year}", index=f"{months[month]}"))
                    if "<title>error page</title>" not in response.text:
                        get_from_pdf(response, month, year)
                    else:
                        print(gov_url.format(month=months[month], year=f"{year}", index=f"{months_full[month]}"))
                        response = requests.get(
                            gov_url.format(month=months[month], year=f"{year}", index=f"{months_full[month]}"))
                        if "<title>error page</title>" not in response.text:
                            get_from_pdf(response, month, year)
    except Exception as e:
        print(e)
        print("error")

def get_from_pdf(response, month, year):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    registered = db.registered.find()
    with io.BytesIO(response.content) as f:
        pdf = PdfFileReader(f)
        numpage = 1
        page = pdf.getPage(numpage)
        page_content = page.extractText()
        pc = page_content.split("\n")
        pc = list(filter(lambda a: a != "" and a != " ", pc))
        print(pc)
        for i in range(len(pc)):
            if pc[i] == '-':
                pc[i + 1] = pc[i] + pc[i + 1]
        for i in range(pc.count("-")):
            pc.remove("-")
        pc = pc[-16:]
        # print the content in the page 20
        print(pc)
        if "-" in pc[3]:
            perc = pc[3].replace("-", "")
            price = pc[1] + " ₪ לליטר"
            message = f"מחיר הדלק הולך לרדת ב{perc} ויעמוד על {price}. כדאי לחכות לתדלק אחריי הירידה."
        else:
            price = pc[1] + " ₪"
            message = f"מחיר הדלק הולך לעלות ב{pc[3]} ויעמוד על {price}. כדאי לתדלק עכשיו."
        for user in registered:
            updater.dispatcher.bot.sendMessage(chat_id=user["_id"], text=message)
        update_fuel_settings(month, year)

def update_fuel_settings(month, year):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    query = {"_id": 1}
    if month == 11:
        month = 0
        year += 1
    else:
        month += 1
    db.settings.replace_one(query, {"_id": 1, "month": month, "year": year})

def register_fuel_notifications(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    chat_id = update.message.chat_id
    db.registered.insert_one({"_id": chat_id})
    update.message.reply_text("you will receive notifications about fuel prices")

def unregister_fuel_notifications(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    chat_id = update.message.chat_id
    db.registered.delete_one({"_id": chat_id})
    update.message.reply_text("you will not receive notifications about fuel prices")


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
    dp.add_handler(CommandHandler("clearmoviealerts", clear_movie_alerts))
    dp.add_handler(CommandHandler("stopbot", stop_bot))
    dp.add_handler(CommandHandler("deletealert", delete_alert))
    dp.add_handler(CommandHandler("alertlist", alert_list))
    dp.add_handler(CommandHandler("coupons", register_coupons))
    dp.add_handler(CommandHandler("unregistercoupons", unregister_coupons))
    dp.add_handler(CommandHandler("commandlist", command_list))
    dp.add_handler(CommandHandler("registerfuelnotifQications", register_fuel_notifications))
    dp.add_handler(CommandHandler("unregisterfuelnotifications", unregister_fuel_notifications))

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