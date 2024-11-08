import time
import pickle
import telebot
import os
import re
import requests
import locale
import datetime
import logging
from telebot import types
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoAlertPresentException

CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")  # Замените на ваш API-ключ CapSolver
CHROMEDRIVER_PATH = "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"
# CHROMEDRIVER_PATH = "/usd/local/bin/chromedriver"
COOKIES_FILE = "cookies.pkl"
CHANNEL_USERNAME = "@kga_korea"

session = requests.Session()

# Configure logging
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Load keys from .env file
load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(bot_token)

# Set locale for number formatting
locale.setlocale(locale.LC_ALL, "en_US.UTF-8")

# Storage for the last error message ID
last_error_message_id = {}

# global variables
car_data = {}
car_id_external = ""
usd_rate = None


# Проверяем подписан ли пользователь на канал
def check_subscription(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if chat_member.status in [
            "member",
            "administrator",
            "creator",
        ]:  # Статус участника
            return True
        else:
            return False
    except Exception as e:
        print(f"Ошибка при проверке подписки: {e}")
        return False


# Функция для создания кнопки "Готово!"
def get_ready_button():
    markup = types.InlineKeyboardMarkup()
    ready_button = types.InlineKeyboardButton("Готово!", callback_data="ready")
    markup.add(ready_button)
    return markup


# Функция для установки команд меню
def set_bot_commands():
    commands = [
        types.BotCommand("start", "Запустить бота"),
        types.BotCommand("cbr", "Курсы валют"),
    ]
    bot.set_my_commands(commands)


# Функция для получения курсов валют с API
def get_currency_rates():
    global usd_rate

    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    response = requests.get(url)
    data = response.json()

    # Получаем курсы валют
    eur_rate = data["Valute"]["EUR"]["Value"]
    usd_rate = data["Valute"]["USD"]["Value"]
    krw_rate = data["Valute"]["KRW"]["Value"] / data["Valute"]["KRW"]["Nominal"]
    cny_rate = data["Valute"]["CNY"]["Value"]

    # Форматируем текст
    rates_text = (
        f"Курс валют ЦБ:\n\n"
        f"EUR {eur_rate:.4f} ₽\n"
        f"USD {usd_rate:.4f} ₽\n"
        f"KRW {krw_rate:.4f} ₽\n"
        f"CNY {cny_rate:.4f} ₽"
    )

    return rates_text


# Обработчик команды /cbr
@bot.message_handler(commands=["cbr"])
def cbr_command(message):
    try:
        rates_text = get_currency_rates()

        # Создаем клавиатуру с кнопкой для расчета автомобиля
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость автомобиля", callback_data="calculate_another"
            )
        )

        # Отправляем сообщение с курсами и клавиатурой
        bot.send_message(message.chat.id, rates_text, reply_markup=keyboard)
    except Exception as e:
        bot.send_message(
            message.chat.id, "Не удалось получить курсы валют. Попробуйте позже."
        )
        print(f"Ошибка при получении курсов валют: {e}")


# Main menu creation function
def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    keyboard.add(
        types.KeyboardButton("Расчёт"),
        types.KeyboardButton("Написать менеджеру"),
        types.KeyboardButton("О компании"),
        types.KeyboardButton("Telegram-канал"),
        types.KeyboardButton("Написать нам в WhatsApp"),
        types.KeyboardButton("Наш Instagram"),
    )
    return keyboard


# Start command handler
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name

    # Проверяем, подписан ли пользователь на канал
    if check_subscription(user_id):
        # Если подписан, отправляем приветственное сообщение и главное меню
        welcome_message = (
            f"Здравствуйте, {user_first_name}!\n"
            "Рад приветствовать вас! Я бот компании KGA KOREA, я помогу вам рассчитать стоимость автомобиля до Владивостока. 🚗💰\n\n"
            "Чем могу помочь?"
        )
        bot.send_message(message.chat.id, welcome_message, reply_markup=main_menu())
    else:
        # Приветственное сообщение
        welcome_message = (
            f"Здравствуйте, {user_first_name}!\n"
            "Рад приветствовать вас! Я бот компании KGA KOREA, я помогу вам рассчитать стоимость автомобиля до Владивостока. 🚗💰\n\n"
            "Для начала, пожалуйста, подпишитесь на канал @kga_korea.\n"
            "Когда будете готовы, нажмите кнопку ниже."
        )
        bot.send_message(
            message.chat.id, welcome_message, reply_markup=get_ready_button()
        )


# Обработка нажатия на кнопку "Готово!"
@bot.callback_query_handler(func=lambda call: call.data == "ready")
def handle_ready_button(call):
    user_id = call.from_user.id

    if check_subscription(user_id):
        bot.answer_callback_query(
            call.id, text="Вы подписаны на канал! Теперь можете использовать бота."
        )
        bot.send_message(
            call.message.chat.id,
            "Теперь вы можете воспользоваться ботом! Чем могу помочь?",
            reply_markup=main_menu(),
        )
    else:
        bot.answer_callback_query(
            call.id, text="Вы не подписаны на канал. Подпишитесь и попробуйте снова."
        )
        bot.send_message(
            call.message.chat.id,
            "Чтобы пользоваться ботом, сначала подпишитесь на канал @kga_korea.",
        )


# Error handling function
def send_error_message(message, error_text):
    global last_error_message_id

    # Remove previous error message if it exists
    if last_error_message_id.get(message.chat.id):
        try:
            bot.delete_message(message.chat.id, last_error_message_id[message.chat.id])
        except Exception as e:
            logging.error(f"Error deleting message: {e}")

    # Send new error message and store its ID
    error_message = bot.reply_to(message, error_text)
    last_error_message_id[message.chat.id] = error_message.id
    logging.error(f"Error sent to user {message.chat.id}: {error_text}")


# def solve_recaptcha_v3():
#     payload = {
#         "clientKey": CAPSOLVER_API_KEY,
#         "task": {
#             "type": "ReCaptchaV3TaskProxyLess",
#             "websiteKey": SITE_KEY,
#             "websiteURL": "http://www.encar.com:80",
#             "pageAction": "/dc/dc_cardetailview_do",
#         },
#     }
#     res = requests.post("https://api.capsolver.com/createTask", json=payload)
#     resp = res.json()
#     task_id = resp.get("taskId")
#     if not task_id:
#         print("Не удалось создать задачу:", res.text)
#         return None
#     print(f"Получен taskId: {task_id} / Ожидание результата...")

#     while True:
#         time.sleep(1)
#         payload = {"clientKey": CAPSOLVER_API_KEY, "taskId": task_id}
#         res = requests.post("https://api.capsolver.com/getTaskResult", json=payload)
#         resp = res.json()
#         if resp.get("status") == "ready":
#             print("reCAPTCHA успешно решена")
#             return resp.get("solution", {}).get("gRecaptchaResponse")
#         if resp.get("status") == "failed" or resp.get("errorId"):
#             print("Решение не удалось! Ответ:", res.text)
#             return None


def save_cookies(driver):
    with open(COOKIES_FILE, "wb") as file:
        pickle.dump(driver.get_cookies(), file)


# Load cookies from file
def load_cookies(driver):
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                driver.add_cookie(cookie)


def check_and_handle_alert(driver, retries=3, wait_time=3):
    for _ in range(retries):
        try:
            # Ждём alert до 5 секунд
            WebDriverWait(driver, wait_time).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print(f"Обнаружено всплывающее окно: {alert.text}")
            alert.accept()  # Закрывает alert
            print("Всплывающее окно было закрыто.")
        except TimeoutException:
            print("Нет активного всплывающего окна.")
            break
        except Exception as alert_exception:
            print(f"Ошибка при обработке alert: {alert_exception}")
            break


def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get(url)
        check_and_handle_alert(driver, retries=5)
        load_cookies(driver)

        # Проверка на наличие reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")
            driver.refresh()
            logging.info("Страница обновлена после reCAPTCHA.")
            check_and_handle_alert(driver)  # Повторная проверка

        save_cookies(driver)
        logging.info("Куки сохранены.")

        # Парсинг URL для car_id
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        # Проверка элемента areaLeaseRent
        try:
            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            print("Элемент areaLeaseRent не найден.")

        # Инициализация переменных
        car_title, car_date, car_engine_capacity, car_price = "", "", "", ""

        # Проверка элемента product_left
        try:
            product_left = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product_left"))
            )
            product_left_splitted = product_left.text.split("\n")
            prod_name = product_left.find_element(By.CLASS_NAME, "prod_name")

            car_title = prod_name.text.strip()
            car_date = product_left_splitted[3]
            car_engine_capacity = product_left_splitted[6]
            car_price = re.sub(r"\D", "", product_left_splitted[1])

        except NoSuchElementException:
            print("Элемент product_left не найден. Переходим к gallery_photo.")
            # Альтернативное получение данных
            try:
                gallery_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.gallery_photo")
                    )
                )
                prod_name = gallery_element.find_element(By.CLASS_NAME, "prod_name")
                car_title = prod_name.text
                items = gallery_element.find_elements(By.XPATH, ".//*")
                for index, item in enumerate(items):
                    if index == 10:
                        car_date = item.text
                    if index == 18:
                        car_engine_capacity = item.text
                try:
                    keyinfo_element = driver.find_element(
                        By.CSS_SELECTOR, "div.wrap_keyinfo"
                    )
                    keyinfo_items = keyinfo_element.find_elements(By.XPATH, ".//*")
                    keyinfo_texts = [
                        item.text for item in keyinfo_items if item.text.strip() != ""
                    ]
                    for index, info in enumerate(keyinfo_texts):
                        if index == 12:
                            car_price = re.sub(r"\D", "", info)
                except NoSuchElementException:
                    print("Элемент wrap_keyinfo не найден.")
            except NoSuchElementException:
                print("Элемент gallery_photo также не найден.")

        # Проверка и форматирование значений
        formatted_price = car_price.replace(",", "") if car_price else "0"
        formatted_engine_capacity = (
            car_engine_capacity.replace(",", "")[0:-2] if car_engine_capacity else "0"
        )
        cleaned_date = "".join(filter(str.isdigit, car_date)) if car_date else "000000"
        formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
        return [new_url, car_title]

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None, None

    finally:
        driver.quit()


# Function to calculate the total cost
def calculate_cost(link, message):
    global car_data

    print("\n\n#################")
    print("НОВЫЙ ЗАПРОС")
    print("#################\n\n")

    bot.send_message(message.chat.id, "Данные переданы в обработку ⏳")

    # Check if the link is from the mobile version
    if "fem.encar.com" in link:
        # Extract all digits from the mobile link
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            # Create the new URL
            link = f"https://www.encar.com/dc/dc_cardetailview.do?carid={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return

    # Get car info and new URL
    result = get_car_info(link)
    time.sleep(5)

    if result is None:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
        )
        return

    new_url, car_title = result

    # Проверка на наличие информации о лизинге
    if not new_url and car_title:
        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Написать менеджеру", url="https://t.me/alekseyan85"
            ),
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            ),
        )
        bot.send_message(
            message.chat.id,
            car_title,  # сообщение что машина лизинговая
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
        return  # Завершаем функцию, чтобы избежать дальнейшей обработки

    if new_url:
        response = requests.get(new_url)

        if response.status_code == 200:
            json_response = response.json()
            car_data = json_response

            # Extract year from the car date string
            year = json_response.get("result")["car"]["date"].split()[-1]
            engine_volume = json_response.get("result")["car"]["engineVolume"]
            price = json_response.get("result")["price"]["car"]["krw"]

            if year and engine_volume and price:
                engine_volume_formatted = f"{format_number(int(engine_volume))} cc"
                age_formatted = calculate_age(year)

                details = {
                    "car_price_korea": json_response.get("result")["price"]["car"][
                        "rub"
                    ],
                    "customs_fee": json_response.get("result")["price"]["russian"][
                        "duty"
                    ]["rub"],
                    "registration": json_response.get("result")["price"]["russian"][
                        "registration"
                    ]["rub"],
                    "sbkts": json_response.get("result")["price"]["russian"]["sbkts"][
                        "rub"
                    ],
                    "svhAndExpertise": json_response.get("result")["price"]["russian"][
                        "svhAndExpertise"
                    ]["rub"],
                }

                # Car's price in KRW
                price_formatted = format_number(price)

                # Price in USD
                total_cost_usd = (
                    details["car_price_korea"] / (usd_rate)
                    + 600
                    + 600
                    + details["customs_fee"] / (usd_rate)
                    + 25000 / usd_rate
                    + details["svhAndExpertise"] / (usd_rate)
                    + details["sbkts"] / (usd_rate)
                )

                # Price in RUB
                total_cost_rub = total_cost_usd * usd_rate

                result_message = (
                    f"Возраст: {age_formatted}\n"
                    f"Стоимость: {price_formatted} KRW\n"
                    f"Объём двигателя: {engine_volume_formatted}\n\n"
                    f"Стоимость автомобиля под ключ до Владивостока: \n**{format_number(total_cost_rub)}₽ / {format_number(total_cost_usd)}$**\n\n"
                    f"🔗 [Ссылка на автомобиль]({link})\n\n"
                    "Если данное авто попадает под санкции, пожалуйста уточните возможность отправки в вашу страну у менеджера @alekseyan85\n\n"
                    "🔗[Официальный телеграм канал](https://t.me/kga_korea)\n"
                )

                bot.send_message(message.chat.id, result_message, parse_mode="Markdown")

                # Inline buttons for further actions
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton(
                        "Детализация расчёта", callback_data="detail"
                    ),
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "Технический отчёт об автомобиле",
                        callback_data="technical_report",
                    ),
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "Связаться с менеджером", url="https://t.me/alekseyan85"
                    ),
                )
                keyboard.add(
                    types.InlineKeyboardButton(
                        "Рассчитать стоимость другого автомобиля",
                        callback_data="calculate_another",
                    ),
                )

                bot.send_message(
                    message.chat.id, "Что делаем дальше?", reply_markup=keyboard
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "🚫 Не удалось извлечь все необходимые данные. Проверьте ссылку.",
                )
        else:
            send_error_message(
                message,
                "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
            )
    else:
        send_error_message(
            message,
            "🚫 Произошла ошибка при получении данных. Проверьте ссылку и попробуйте снова.",
        )


# Function to get insurance total
def get_insurance_total():
    print("\n\n####################")
    print("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧËТ ОБ АВТОМОБИЛЕ")
    print("####################\n\n")

    global car_id_external

    # Настройка WebDriver с нужными опциями
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    service = Service(CHROMEDRIVER_PATH)

    # Формируем URL
    url = f"http://www.encar.com/dc/dc_cardetailview.do?method=kidiFirstPop&carid={car_id_external}&wtClick_carview=044"

    try:
        # Запускаем WebDriver
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        # Пробуем найти элемент 'smlist' без явного ожидания
        time.sleep(2)
        try:
            smlist_element = driver.find_element(By.CLASS_NAME, "smlist")
        except NoSuchElementException:
            print("Элемент 'smlist' не найден.")
            return ["Нет данных", "Нет данных"]

        # Находим таблицу
        table = smlist_element.find_element(By.TAG_NAME, "table")
        rows = table.find_elements(By.TAG_NAME, "tr")

        # Извлекаем данные
        damage_to_my_car = (
            rows[4].find_elements(By.TAG_NAME, "td")[1].text if len(rows) > 4 else "0"
        )
        damage_to_other_car = (
            rows[5].find_elements(By.TAG_NAME, "td")[1].text if len(rows) > 5 else "0"
        )

        # Упрощенная функция для извлечения числа
        def extract_large_number(damage_text):
            if "없음" in damage_text:
                return "0"
            numbers = re.findall(r"[\d,]+(?=\s*원)", damage_text)
            return numbers[0] if numbers else "0"

        # Форматируем данные
        damage_to_my_car_formatted = extract_large_number(damage_to_my_car)
        damage_to_other_car_formatted = extract_large_number(damage_to_other_car)

        return [damage_to_my_car_formatted, damage_to_other_car_formatted]

    except Exception as e:
        print(f"Произошла ошибка при получении данных: {e}")
        return ["Ошибка при получении данных", ""]

    finally:
        driver.quit()


# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    global car_data, car_id_external, usd_rate

    if call.data.startswith("detail"):
        print("\n\n####################")
        print("[ЗАПРОС] ДЕТАЛИЗАЦИЯ РАСЧËТА")
        print("####################\n\n")

        details = {
            "car_price_korea": car_data.get("result")["price"]["car"]["rub"],
            "customs_fee": car_data.get("result")["price"]["russian"]["duty"]["rub"],
            "registration": car_data.get("result")["price"]["russian"]["registration"][
                "rub"
            ],
            "sbkts": car_data.get("result")["price"]["russian"]["sbkts"]["rub"],
            "svhAndExpertise": car_data.get("result")["price"]["russian"][
                "svhAndExpertise"
            ]["rub"],
        }

        # Formatted numbers
        car_price_formatted = format_number(details["car_price_korea"] / (usd_rate))
        kga_export_service_fee_formatted = format_number(600)
        delivery_fee_formatted = format_number(600)
        customs_fee_formatted = format_number(details["customs_fee"] / (usd_rate))
        registration_fee_formatted = format_number(25000 / usd_rate)
        sbkts_formatted = format_number(details["svhAndExpertise"] / (usd_rate))
        svh_formatted = format_number(details["sbkts"] / (usd_rate))

        # Construct cost breakdown message
        detail_message = (
            "📝 Детализация расчёта:\n\n"
            f"Стоимость авто: <b>{car_price_formatted}$</b>\n\n"
            f"Услуги KGA Korea: <b>{kga_export_service_fee_formatted}$</b>\n\n"
            f"Доставка до Владивостока: <b>{delivery_fee_formatted}$</b>\n\n"
            f"Растаможка: <b>{customs_fee_formatted}$</b>\n\n"
            f"Оформление / Брокер: <b>{registration_fee_formatted}$</b>\n\n"
            f"СБКТС / ЭПТС: <b>{sbkts_formatted}$</b>\n\n"
            f"СВХ / Выгрузка: <b>{svh_formatted}$</b>\n\n\n"
            f"<b>ПРИМЕЧАНИЕ: </b> В дальнейшем наш менеджер предоставит вам точный расчёт стоимости, учитывая актуальный курс валют на <b style='text-transform: uppercase;'>день оформления</b>. Так как стоимость авто зависит от курса корейской воны и доллара, а стоимость растаможки в РФ - от курса евро.\n\nНе волнуйтесь, если цена немного изменится - это нормально. Ваше доверие - наш главный приоритет!\n\n"
        )

        bot.send_message(call.message.chat.id, detail_message, parse_mode="HTML")

        # Inline buttons for further actions
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "Рассчитать стоимость другого автомобиля",
                callback_data="calculate_another",
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "Связаться с менеджером", url="https://t.me/alekseyan85"
            )
        )

        bot.send_message(
            call.message.chat.id, "Что делаем дальше?", reply_markup=keyboard
        )

    elif call.data == "technical_report":
        # Retrieve insurance information
        insurance_info = get_insurance_total()

        # Проверка на наличие ошибки
        if "Ошибка" in insurance_info[0] or "Ошибка" in insurance_info[1]:
            error_message = (
                "Страховая история недоступна. \n\n"
                f'<a href="https://fem.encar.com/cars/detail/{car_id_external}">🔗 Ссылка на автомобиль 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/alekseyan85"
                )
            )

            # Отправка сообщения об ошибке
            bot.send_message(
                call.message.chat.id,
                error_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        else:
            current_car_insurance_payments = (
                "0" if len(insurance_info[0]) == 0 else insurance_info[0]
            )
            other_car_insurance_payments = (
                "0" if len(insurance_info[1]) == 0 else insurance_info[1]
            )

            # Construct the message for the technical report
            tech_report_message = (
                f"Страховые выплаты по представленному автомобилю: \n<b>{current_car_insurance_payments} ₩</b>\n\n"
                f"Страховые выплаты другим участникам ДТП: \n<b>{other_car_insurance_payments} ₩</b>\n\n"
                f'<a href="https://fem.encar.com/cars/report/inspect/{car_id_external}">🔗 Ссылка на схему повреждений кузовных элементов 🔗</a>'
            )

            # Inline buttons for further actions
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "Рассчитать стоимость другого автомобиля",
                    callback_data="calculate_another",
                )
            )
            keyboard.add(
                types.InlineKeyboardButton(
                    "Связаться с менеджером", url="https://t.me/alekseyan85"
                )
            )

            bot.send_message(
                call.message.chat.id,
                tech_report_message,
                parse_mode="HTML",
                reply_markup=keyboard,
            )

    elif call.data == "calculate_another":
        bot.send_message(
            call.message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_message = message.text.strip()

    # Проверяем нажатие кнопки "Рассчитать автомобиль"
    if user_message == "Расчёт":
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите ссылку на автомобиль с сайта www.encar.com:",
        )

    # Проверка на корректность ссылки
    elif re.match(r"^https?://(www|fem)\.encar\.com/.*", user_message):
        calculate_cost(user_message, message)

    # Проверка на другие команды
    elif user_message == "Написать менеджеру":
        bot.send_message(
            message.chat.id, "Вы можете связаться с менеджером по ссылке: @alekseyan85"
        )

    elif user_message == "Написать нам в WhatsApp":
        whatsapp_link = "https://wa.me/821049911282"
        bot.send_message(
            message.chat.id,
            f"Вы можете связаться с нами через WhatsApp по ссылке: {whatsapp_link}",
        )

    elif user_message == "О компании":
        about_message = "KGA KOREA — ваш надёжный друг в мире автомобилей из Южной Кореи. Мы работаем напрямую, без посредников! Наше обещание: никаких скрытых условий, только прозрачный и честный подход к каждому клиенту!"
        bot.send_message(message.chat.id, about_message)

    elif user_message == "Telegram-канал":
        channel_link = "https://t.me/kga_korea"
        bot.send_message(
            message.chat.id, f"Подписывайтесь на наш Telegram-канал: {channel_link}"
        )
    elif user_message == "Наш Instagram":
        instagram_link = "https://www.instagram.com/kgakorea/"
        bot.send_message(message.chat.id, f"Посетите наш Instagram: {instagram_link}")

    # Если сообщение не соответствует ни одному из условий
    else:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите корректную ссылку на автомобиль с сайта www.encar.com или fem.encar.com.",
        )


# Utility function to calculate the age category
def calculate_age(year):
    current_year = datetime.datetime.now().year
    age = current_year - int(year)

    if age < 3:
        return f"До 3 лет"
    elif 3 <= age < 5:
        return f"от 3 до 5 лет"
    else:
        return f"от 5 лет"


def format_number(number):
    number = float(number) if isinstance(number, str) else number
    return locale.format_string("%d", number, grouping=True)


# Run the bot
if __name__ == "__main__":
    get_currency_rates()
    set_bot_commands()
    bot.polling(none_stop=True)


# UNUSED CODE
# recaptcha_response = solve_recaptcha_v3()

# if recaptcha_response:
#     # Ждем, пока элемент g-recaptcha-response станет доступен
#     try:
#         wait = WebDriverWait(driver, 1)  # Ожидание до 10 секунд
#         recaptcha_element = wait.until(
#             EC.presence_of_element_located((By.ID, "g-recaptcha-response"))
#         )

#         # Заполняем g-recaptcha-response
#         driver.execute_script(
#             f'document.getElementById("g-recaptcha-response").innerHTML = "{recaptcha_response}";'
#         )

#         # Отправляем форму
#         driver.execute_script("document.forms[0].submit();")
#         time.sleep(1)  # Подождите, чтобы страница успела загрузиться

#         check_and_handle_alert(driver)

#         # Обновите URL после отправки формы
#         driver.get(url)

#         check_and_handle_alert(driver)
#     except TimeoutException:
#         print(
#             "Элемент g-recaptcha-response не был найден в течение 10 секунд."
#         )
