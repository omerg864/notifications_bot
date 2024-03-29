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

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ActionChains

from webdriver_manager.chrome import ChromeDriverManager

from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from dotenv import load_dotenv

load_dotenv()


DEBUG = os.environ.get("DEBUG_VALUE") == "True"
PORT = int(os.environ.get('PORT', 8443))

coupons_url = os.environ.get("COUPONS_URL")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = os.environ.get("NOTIFICATIONS_BOT_TOKEN")

updater = Updater(TOKEN, use_context=True)

commands = ["moviealert - following imdb url to add to your movie alert list", "deletealert - following imdb url to delete from your movie alert list",
            "moviealertlist - list of your movie alerts", "clearmoviealerts - delete all of your movie alerts", f"coupons - register to receive Udemy 100% off coupons",
            "unregistercoupons - unregister from receiving Udemy coupons", "fuelcosts - register to receive israel fuel costs notifications on change",
            "unregisterfuelnotifications - unregister from receiving fuel costs notifications", "alertlist - list of all registered services" 
            ,"waitcoupons - not sending new coupons and holding them until you exit wait mode", "exitwaitcoupons - send all gathered coupons while being in wait mode",
             "managercommands - list of manager command require password", "stopbot - stops the bot and deletes your alert list"]

manager_commands = ["All commands here require admin password after the command and arguments can be inserted after that:", "managercommands - list of manager command require password",
                    "craeteorg - create a new organization in mishmar ramla with gived date: YYYY-MM-DD", "echo - send message to all users using the bot",
                    "getregistered - get users registered to the bot and services", "changepass - change admin's password"]


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    print("started")
    chat_id = update.message.chat_id
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.manager
    if db.registered.find_one({"_id": chat_id}) is None:
        db.registered.insert_one({"_id": chat_id})
    update.message.reply_text('Hi! check out the commands with /help')
    update.message.reply_text('Also some times the server takes a while (about 30 seconds) to respond, so be patient!')

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

def get_driver():
    software_names = [SoftwareName.CHROME.value]
    operating_systems = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]

    user_agent_rotator = UserAgent(software_names=software_names, operating_systems=operating_systems, limit=100)

    user_agent = user_agent_rotator.get_random_user_agent()

    chrome_options = Options()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1420,1080')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument(f'--user-agent={user_agent}')

    s=Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=s, options=chrome_options)
    return driver


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
    db = client.manager
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
        movie_name1 = ''.join(char for char in movie_name if char.isalnum() or char == ' ' or char == '-')
        movie_name1 = movie_name1.replace(" ", "-").lower() + "-" + str(year)
        movie_link = f"https://yts.mx/movies/{movie_name1}"
        to_db(chat_id, movie_name, movie_link)
        update.message.reply_text("You will be notified when " + movie_name + " is released!")
    except Exception as e:
        print(e)
        update.message.reply_text("Invalid URL. Try something like this: /moviealert https://imdb.com/title/tt0111161/")

def remove_from_db(url, chat_id):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    db.alerts.delete_many({"chat_id": chat_id, "movie_link": url})

def movie_alert_list(update, context):
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
        update.message.reply_text("Invalid URL. Try something like this: /moviealert https://imdb.com/title/tt0111161/")

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
    print("Checking movies...")
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.movie_alerts
    movies = db.alerts.find()
    for movie in movies:
        movie_link = movie['movie_link']
        r = requests.get(movie_link, headers={'User-Agent': 'Mozilla/5.0'}).text
        soup = BeautifulSoup(r, 'html.parser')
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
    if db.registered.find_one({"_id": update.message.chat_id}) is None:
        db.registered.insert_one({"_id": update.message.chat_id})
        update.message.reply_text("You are now registered for coupons alerts!")
    else:
        update.message.reply_text("You are already registered for coupons alerts!")

def unregister_coupons(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    if db.registered.find_one({"_id": update.message.chat_id}) is not None:
        db.registered.delete_one({"_id": update.message.chat_id})
        update.message.reply_text("You are now unregistered for coupons alerts!")
    else:
        update.message.reply_text("You are not registered for coupons alerts!")

def coupon_scrape(url):
    try:
        response = requests.get(coupons_url, headers={'User-Agent': 'Mozilla/5.0'}).text
        soup = BeautifulSoup(response, "html.parser")
        list_of_coupons = soup.find("div", {"class": "eq_grid pt5 rh-flex-eq-height col_wrap_three"})
        articles = list_of_coupons.find_all("article")
        first_name = articles[0].find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
        first_coupon_url = first_name.find("a")["href"]
        second_name = articles[1].find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
        second_coupon_url = second_name.find("a")["href"]
        urls2 = [first_coupon_url, second_coupon_url]
        new_coupons, urls = connect_to_db_coupons(urls2, True)
        print(urls2)
        if new_coupons:
            courses = []
            hit = False
            index = 0
            for article in articles:
                try:
                    name = article.find("h3", {"class": "flowhidden mb10 fontnormal position-relative"})
                    coupon_url = name.find("a")["href"]
                    if index != 0:
                        if coupon_url in urls:
                            hit = True
                            break
                    else:
                        if coupon_url == urls[0]:
                            hit = True
                            break
                    percent = article.find("span", {"class": "grid_onsale"}).text
                    if "100%" not in percent:
                        continue
                    image = article.find("img", {"class": "ezlazyload"})["data-ezsrc"]
                    time.sleep(4)
                    courses.append({"name": name.text, "url": coupon_url, "image": image, "percent": percent})
                except Exception as e:
                    print(e)
                    print("False coupon found")
                index += 1
            if index < 11:
                for course in courses:
                    send_coupons(course["name"], course["percent"], course["url"], course["image"])
            else:
                send_coupons_list(courses)
            return [new_coupons, hit, urls2]
    except Exception as e:
        print(e)
        return False
    return [new_coupons]

def get_coupons():
    ##"""Get the coupons from the website."""
    print("Checking coupons...")
    try:
        out = coupon_scrape(coupons_url)
        if out[0]:
            if not out[1]:
                print("page 2")
                coupon_scrape(coupons_url + 'page/2/')
            connect_to_db_coupons(out[2], False)
    except Exception as e:
        print(e)

def connect_to_db_coupons(urls, read):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    if not read:
        query = {"_id" : 1 }
        db.coupons.replace_one(query ,{"url": urls[0], "url2": urls[1], "_id" : 1})
    else:
        settings = db.coupons.find_one({"_id": 1})
        urls2 = [settings["url"], settings["url2"]]
        if urls[0] == urls2[0] or urls[1] == urls2[1]:
            print("No new coupons found")
            return [False, urls2]
        return [True, urls2]

def send_coupons(name, percent, coupon_url, image):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    chat_ids = db.registered.find()
    for chat_id in chat_ids:
        is_waiting = db.waiting.find_one({"_id": chat_id['_id']})
        if is_waiting != None:
            db.gathered.insert_one({"chat_id": chat_id['_id'], "name": name, "coupon_url": coupon_url, "image": image, "percent": percent})
            print("Added to waiting list")
        else:
            updater.dispatcher.bot.sendPhoto(chat_id=chat_id["_id"], photo=image, caption=f'{name} is {percent}: {coupon_url}')
            print("sent coupon")

def send_coupons_list(coupons):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    chat_ids = db.registered.find()
    message = ""
    index = 1
    for coupon in coupons:
        name = coupon["name"]
        percent = coupon["percent"]
        coupon_url = coupon["url"]
        message += f"{index}. {name} is {percent}: {coupon_url}\n"
    for chat_id in chat_ids:
        is_waiting = db.waiting.find_one({"_id": chat_id['_id']})
        if is_waiting != None:
            for coupon in coupons:
                db.gathered.insert_one({"chat_id": chat_id['_id'], "name": coupon['name'], "coupon_url": coupon['coupon_url'], "image": coupon['image'], "percent": coupon['percent']})
                print("Added to waiting list")
        else:
            updater.dispatcher.bot.sendMessage(chat_id=chat_id["_id"], text=message)
            print("sent coupons list")


def get_fuel_settings():
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    fuel_settings = db.settings.find_one({"_id": 1})
    return fuel_settings["month"], fuel_settings["year"]

def get_data_from_gov():
    print("Checking fuel costs...")
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
        for i in range(len(pc)):
            if pc[i] == '-':
                pc[i + 1] = pc[i] + pc[i + 1]
        for i in range(pc.count("-")):
            pc.remove("-")
        pc = pc[-16:]
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
    if db.registered.find_one({"_id": chat_id}) == None:
        db.registered.insert_one({"_id": chat_id})
        update.message.reply_text("You will receive notifications about fuel prices")
    else:
        update.message.reply_text("You are already registered")

def unregister_fuel_notifications(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    chat_id = update.message.chat_id
    if db.registered.find_one({"_id": chat_id}) != None:
        db.registered.delete_one({"_id": chat_id})
        update.message.reply_text("You will not receive notifications about fuel prices")
    else:
        update.message.reply_text("You are not registered")

def alert_list(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.fuel
    chat_id = update.message.chat_id
    fuel = db.registered.find_one({"_id": chat_id})
    message = "Registered services:\n"
    index = 1
    if fuel != None:
        message += str(index) + ". " + "Israel fuel costs notifications" + "\n"
        index += 1
    db = client.new_database
    coupon = db.registered.find_one({"_id": chat_id})
    if coupon != None:
        message += str(index) + ". " + "Udemy 100% off coupon notifications" + "\n"
        index += 1
    db = client.movie_alerts
    movie = db.alerts.find({"chat_id": chat_id})
    if movie != None:
        message += str(index) + ". " + "Movie notifications" + "\n"
        index += 1
    if index == 1:
        update.message.reply_text("you are not registered for any notifications")
    else:
        update.message.reply_text(message)

def create_organization(date):
    driver = get_driver()
    base_url = "http://mishmarramla.herokuapp.com/"
    driver.maximize_window()
    driver.get(base_url)
    driver.implicitly_wait(10)
    user_name = os.environ.get("MISHMAR_RAMLA_ADMIN")
    password = os.environ.get("MISHMAR_RAMLA_ADMIN_PASS")
    xpathA = '//a[contains(@href, \'{0}\')]'
    xpathInput = '//input[contains(@name, \'{0}\')]'
    xpathButton = '//button[contains(@type, \'{0}\')]'
    # get if logged in
    try:
        print("logging in")
        # login link
        driver.find_element(By.XPATH, xpathA.format('login')).click()
        # username
        driver.find_element(By.XPATH, xpathInput.format("username")).send_keys(user_name)
        # password
        driver.find_element(By.XPATH, xpathInput.format("password")).send_keys(password)
        # login button
        driver.find_element(By.XPATH, xpathButton.format('submit')).click()
    except WebDriverException:
        print("Already logged in")
    # Go to admin site and create new organization
    try:
        print("creating new organization")
        # admin site button
        driver.find_element(By.XPATH, xpathA.format('https://mishmarramla.herokuapp.com/admin')).click()
        # go to organizations
        driver.find_element(By.XPATH, xpathA.format('/admin/Schedule/organization/')).click()
        # get table
        dates = driver.find_element(By.ID, "result_list").find_elements(By.TAG_NAME, "a")
        exist = False
        for d in dates:
            if d.text == date:
                exist = True
        # passed organization
        print("passed organization")
        print(exist)
        if not exist:
            # new organization button
            driver.find_element(By.XPATH, xpathA.format('/admin/Schedule/organization/add/')).click()
            # enter date
            dateE = driver.find_element(By.XPATH, xpathInput.format("date"))
            dateE.clear()
            dateE.send_keys(date)
            # save button
            driver.find_element(By.XPATH, xpathInput.format("_save")).click()
            print("created organization")
        # go to home
        driver.get(base_url)
        # go to settings
        driver.find_element(By.XPATH, xpathA.format('/settings/')).click()
        # get checkbox
        checkbox = driver.find_element(By.NAME, "serv")
        print("passed checkbox")
        if checkbox.is_selected():
            checkbox.click()
            print("checked checkbox")
            # save changes
            driver.find_element(By.XPATH, xpathButton.format('submit')).click()
            print("saved changes")
        else:
            print("checkbox already checked")
        time.sleep(4)
        driver.quit()
        return True
    except WebDriverException:
        print("ERROR")
    time.sleep(10)
    driver.quit()
    return False

def get_manager_settings():
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.manager
    settings = db.settings.find_one({"_id": 1})
    return settings

def create_org(update, context):
    message = update.message.text
    message = message.replace("/createorg ", "").split(" ")
    settings = get_manager_settings()
    accepted = False
    if message[0] == settings["password"]:
        accepted = True
    if accepted:
        update.message.reply_text("Password accepted")
        date = message[1]
        if create_organization(date):
            update.message.reply_text("Organization created")
        else:
            update.message.reply_text("Could not create organization")
    else:
        update.message.reply_text("Wrong password")

def wait_coupons(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    chat_id = update.message.chat_id
    coupon = db.waiting.find_one({"_id": chat_id})
    if coupon != None:
        update.message.reply_text("You are already in wait mode")
    else:
        sub = db.registered.find_one({"_id": chat_id})
        if sub != None:
            update.message.reply_text("Entered wait mode. In the meantime the coupons are gathered and will be sent when you exit wait mode")
            db.waiting.insert_one({"_id": chat_id})
        else:
            update.message.reply_text("First register for coupons notifications using /coupons")

def exit_wait_coupons(update, context):
    ca = certifi.where()
    client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=ca)
    db = client.new_database
    chat_id = update.message.chat_id
    coupon = db.waiting.find_one({"_id": chat_id})
    if coupon != None:
        db.waiting.delete_one({"_id": chat_id})
        update.message.reply_text("Exited wait mode. sending coupons gathered")
        coupons = db.gathered.find({"chat_id": chat_id})
        sent = False
        for c in coupons:
            sent = True
            name = c["name"]
            coupon_url = c["coupon_url"]
            percent = c["percent"]
            updater.dispatcher.bot.sendPhoto(chat_id=chat_id, photo=c["image"], caption=f'{name} is {percent}: {coupon_url}')
            db.gathered.delete_one({"_id": c["_id"]})
        if not sent:
            update.message.reply_text("No coupons gathered")
    else:
        update.message.reply_text("You are not in wait mode")

def get_chat_id(update, context):
    update.message.reply_text(update.message.chat_id)

def echo_message(update, context):
    message = update.message.text
    message = message.replace("/echo ", "").split(" ")
    settings = get_manager_settings()
    accepted = False
    if message[0] == settings["password"]:
        accepted = True
    if accepted:
        update.message.reply_text("Password accepted")
        echo = message[1]
        CA = certifi.where()
        client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=CA)
        db = client.manager
        chats = db.registered.find()
        for chat in chats:
            updater.dispatcher.bot.send_message(chat_id=chat["_id"], text=echo)
            print("sent to " + str(chat["_id"]))
    else:
        update.message.reply_text("Wrong password")


def get_registered(update, context):
    message = update.message.text
    message = message.replace("/getregistered ", "").split(" ")
    settings = get_manager_settings()
    accepted = False
    if message[0] == settings["password"]:
        accepted = True
    if accepted:
        update.message.reply_text("Password accepted")
        CA = certifi.where()
        client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=CA)
        db = client.manager
        count = 0
        chats = db.registered.find()
        for chat in chats:
            count += 1
        message = f"Pepole with active bot : {count}\n"
        db = client.new_database
        reg = db.registered.find()
        count = 0
        for r in reg:
            count += 1
        message += f'People registered for coupons : {count}\n'
        db = client.fuel
        reg = db.registered.find()
        count = 0
        for r in reg:
            count += 1
        message += f'People registered for fuel notifications : {count}\n'
        db = client.movie_alerts
        reg = db.alerts.find()
        count = 0
        for r in reg:
            count += 1
        message += f'movies alerts : {count}\n'
        update.message.reply_text(message)
    else:
        update.message.reply_text("Wrong password")

def change_password(update, context):
    message = update.message.text
    message = message.replace("/changepass ", "").split(" ")
    settings = get_manager_settings()
    accepted = False
    if message[0] == settings["password"]:
        accepted = True
    if accepted:
        update.message.reply_text("Password accepted")
        new_password = message[1]
        CA = certifi.where()
        client = pymongo.MongoClient(os.environ.get("MONGODB_ACCESS"), tlsCAFile=CA)
        db = client.manager
        db.settings.update_one({"_id": 1}, {"$set": {"password": new_password}})
        update.message.reply_text("Password changed")
    else:
        update.message.reply_text("Wrong password")

def manager_list(update, context):
    message = update.message.text
    message = message.replace("/managercommands ", "").split(" ")
    settings = get_manager_settings()
    accepted = False
    if message[0] == settings["password"]:
        accepted = True
    if accepted:
        message = ""
        if len(manager_commands) > 1:
            for command in manager_commands:
                message += command + "\n"
            update.message.reply_text(message)
        else:
            update.message.reply_text("Can't help you! good luck!")
    else:
        update.message.reply_text("Wrong password")



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
    dp.add_handler(CommandHandler("moviealertlist", movie_alert_list))
    dp.add_handler(CommandHandler("coupons", register_coupons))
    dp.add_handler(CommandHandler("unregistercoupons", unregister_coupons))
    dp.add_handler(CommandHandler("commandlist", command_list))
    dp.add_handler(CommandHandler("fuelcosts", register_fuel_notifications))
    dp.add_handler(CommandHandler("unregisterfuelnotifications", unregister_fuel_notifications))
    dp.add_handler(CommandHandler("alertlist", alert_list))
    dp.add_handler(CommandHandler("waitcoupons", wait_coupons))
    dp.add_handler(CommandHandler("exitwaitcoupons", exit_wait_coupons))
    dp.add_handler(CommandHandler("chatid", get_chat_id))
    dp.add_handler(CommandHandler("managercommands", manager_list))


    # manager commands

    dp.add_handler(CommandHandler("createorg", create_org))
    dp.add_handler(CommandHandler("echo", echo_message))
    dp.add_handler(CommandHandler("getregistered", get_registered))
    dp.add_handler(CommandHandler("changepass", change_password))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN,
                      webhook_url="https://www.notifications-bot-fdph.onrender.com/" + TOKEN)

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()