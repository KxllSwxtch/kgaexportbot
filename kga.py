import time
import pickle
import telebot
import os
import re
import requests
import locale
import datetime
import logging

from twocaptcha import TwoCaptcha
from telebot import types
from dotenv import load_dotenv
from seleniumwire import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")  # Замените на ваш API-ключ CapSolver
# CHROMEDRIVER_PATH = "/app/.chrome-for-testing/chromedriver-linux64/chromedriver"
CHROMEDRIVER_PATH = "/opt/homebrew/bin/chromedriver"
CHANNEL_USERNAME = "@kga_korea"

# Proxy
PROXY_IP = "45.118.250.2"
PROXY_PORT = "8000"
PROXY_USER = "B01vby"
PROXY_PASS = "GBno0x"

proxy = {
    "http": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}",
    "https": f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_IP}:{PROXY_PORT}",
}


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


def print_message(msg: str):
    print("\n\n#####################")
    print(msg)
    print("#####################\n\n")
    return None


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

    print_message("ПОЛУЧАЕМ КУРС ЦБ")

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

    print(f"{rates_text}\n\n")
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


def get_ip():
    response = requests.get(
        "https://api.ipify.org?format=json", verify=True, proxies=proxy
    )
    ip = response.json()["ip"]
    return ip


# print_message(f"Current IP address: {get_ip()}")


def extract_sitekey(driver, url):
    driver.get(url)

    iframe = driver.find_element(By.TAG_NAME, "iframe")
    iframe_src = iframe.get_attribute("src")
    match = re.search(r"k=([A-Za-z0-9_-]+)", iframe_src)

    if match:
        sitekey = match.group(1)
        return sitekey
    else:
        return None


def send_recaptcha_token(token):
    data = {"token": token, "action": "/dc/dc_cardetailview.do"}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "http://www.encar.com/index.do",
    }

    url = "https://www.encar.com/validation_recaptcha.do?method=v3"
    # Отправляем POST-запрос с токеном
    response = requests.post(
        url, data=data, headers=headers, proxies=proxy, verify=True
    )

    # Выводим ответ для отладки
    print("\n\nОтвет от сервера:")
    print(f"Статус код: {response.status_code}")
    print(f"Тело ответа: {response.text}\n\n")

    try:
        result = response.json()

        if result[0]["success"]:
            print("reCAPTCHA успешно пройдена!")
            return True
        else:
            print("Ошибка проверки reCAPTCHA.")
            return False
    except requests.exceptions.JSONDecodeError:
        print("Ошибка: Ответ от сервера не является валидным JSON.")
        return False
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return False


def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--ignore-certificate-errors-spki-list")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.6723.92 Safari/537.36"
    )

    prefs = {
        "profile.default_content_setting_values.notifications": 2,  # Отключить уведомления
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    seleniumwire_options = {"proxy": proxy}

    driver = webdriver.Chrome(
        options=chrome_options, seleniumwire_options=seleniumwire_options
    )

    return driver


def get_car_info(url):
    global car_id_external

    driver = create_driver()

    # Извлекаем carid с URL encar
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    car_id = query_params.get("carid", [None])[0]

    try:
        # solver = TwoCaptcha("89a8f41a0641f085c8ca6e861e0fa571")

        is_recaptcha_solved = True

        driver.get(url)
        time.sleep(3)

        # if "reCAPTCHA" in driver.page_source:
        #     is_recaptcha_solved = False
        #     print_message("Обнаружена reCAPTCHA, решаем...")

        #     sitekey = extract_sitekey(driver, url)
        #     print(f"Sitekey: {sitekey}")

        #     result = solver.recaptcha(sitekey, url)
        #     print(f'reCAPTCHA result: {result["code"][0:50]}...')

        #     is_recaptcha_solved = send_recaptcha_token(result["code"])

        if is_recaptcha_solved:
            # Достаём данные об авто после решения капчи
            car_date, car_price, car_engine_displacement, car_title = "", "", "", ""

            price_el = driver.find_element(By.CLASS_NAME, "DetailLeadCase_point__vdG4b")
            car_price = re.sub(r"\D", "", price_el.text)
            time.sleep(3)

            button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), '자세히')]")
                )
            )
            button.click()
            time.sleep(2)

            content = driver.find_element(
                By.CLASS_NAME,
                "BottomSheet-module_bottom_sheet__LeljN",
            )
            splitted_content = content.text.split("\n")
            car_engine_displacement = re.sub(r"\D", "", splitted_content[9])

            car_date = splitted_content[5]
            year = car_date.split("년")[0].strip()  # Получаем '24'
            month = car_date.split("년")[1].replace("월", "").strip()  # Получаем '02'
            formatted_car_date = f"01{month}{year}"

            print(car_title)
            print(f"Registration Date: {formatted_car_date}")
            print(f"Car Engine Displacement: {car_engine_displacement}")
            print(f"Price: {car_price}")

            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={car_price}&date={formatted_car_date}&volume={car_engine_displacement}"

            driver.quit()
            return [new_url, car_title]

    except WebDriverException as e:
        print(f"Ошибка Selenium: {e}")
        driver.quit()
        return ["", "Произошла ошибка получения данных..."]

    return ["", ""]


# Function to calculate the total cost
def calculate_cost(link, message):
    global car_data
    print_message("ЗАПРОС НА РАСЧËТ АВТОМОБИЛЯ")

    bot.send_message(
        message.chat.id, "Данные переданы в обработку. Пожалуйста подождите ⏳"
    )

    parsed_url = urlparse(link)
    query_params = parse_qs(parsed_url.query)
    car_id = query_params.get("carid", [None])[0]

    # Check if the link is from the mobile version
    if "fem.encar.com" in link:
        # Extract all digits from the mobile link
        car_id_match = re.findall(r"\d+", link)
        if car_id_match:
            car_id = car_id_match[0]  # Use the first match of digits
            # Create the new URL
            link = f"http://www.encar.com/dc/dc_cardetailview.do?carid={car_id}"
        else:
            send_error_message(message, "🚫 Не удалось извлечь carid из ссылки.")
            return

    link = f"https://fem.encar.com/cars/detail/{car_id}"
    # Get car info and new URL
    result = get_car_info(link)

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

                preview_link = f"https://fem.encar.com/cars/detail/{car_id}"

                result_message = (
                    f"Возраст: {age_formatted}\n"
                    f"Стоимость: {price_formatted} KRW\n"
                    f"Объём двигателя: {engine_volume_formatted}\n\n"
                    f"Стоимость автомобиля под ключ до Владивостока: \n**{format_number(total_cost_rub)}₽ / {format_number(total_cost_usd)}$**\n\n"
                    f"🔗 [Ссылка на автомобиль]({preview_link})\n\n"
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
    print_message("[ЗАПРОС] ТЕХНИЧЕСКИЙ ОТЧËТ ОБ АВТОМОБИЛЕ")

    global car_id_external

    url = f"https://fem.encar.com/cars/report/accident/{car_id_external}"
    driver = create_driver()

    try:
        driver.get(url)

        # Пробуем найти элемент 'smlist' без явного ожидания
        try:
            report_accident_summary_element = driver.find_element(
                By.CLASS_NAME, "ReportAccidentSummary_list_accident__q6vLx"
            )
        except NoSuchElementException:
            print("Элемент 'ReportAccidentSummary_list_accident__q6vLx' не найден.")
            return ["Нет данных", "Нет данных"]

        report_accident_summary_element_splitted = (
            report_accident_summary_element.text.split("\n")
        )

        # Извлекаем данные
        damage_to_my_car = (
            report_accident_summary_element_splitted[4]
            if len(report_accident_summary_element.text) > 4
            else "0"
        )
        damage_to_other_car = (
            report_accident_summary_element_splitted[5]
            if len(report_accident_summary_element.text) > 5
            else "0"
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
