import requests
import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from twocaptcha import TwoCaptcha

# Настройка прокси
proxies = {
    "http": "http://B01vby:GBno0x@45.118.250.2:8000",
    "https": "http://B01vby:GBno0x@45.118.250.2:8000",
}

# Создание экземпляра 2Captcha
solver = TwoCaptcha("89a8f41a0641f085c8ca6e861e0fa571")

# URL страницы
url = "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=word&carid=37737638&view_type=normal&wtClick_forList=017&advClickPosition=imp_word_p1_g8"


# Функция для настройки Selenium с прокси
def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")  # Необходим для работы в Heroku
    chrome_options.add_argument("--disable-dev-shm-usage")  # Решает проблемы с памятью
    chrome_options.add_argument("--window-size=1920,1080")  # Устанавливает размер окна
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--v=1")  # Уровень логирования
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
    )

    # Прокси для Selenium
    webdriver.DesiredCapabilities.CHROME["proxy"] = {
        "httpProxy": "45.118.250.2:8000",
        "sslProxy": "45.118.250.2:8000",
        "proxyType": "MANUAL",
    }

    # Запуск браузера
    driver = webdriver.Chrome(options=chrome_options)
    return driver


# Запуск браузера и получение токена reCAPTCHA
def get_car_info(url):
    driver = create_driver()

    try:
        # Открываем начальную страницу (если нужно)
        driver.get("http://encar.com")

        # Открываем страницу с автомобилем
        driver.get(url)

        # Ищем sitekey для reCAPTCHA
        sitekey_element = driver.find_element(By.CSS_SELECTOR, ".g-recaptcha")
        sitekey = sitekey_element.get_attribute("data-sitekey")
        print(f"Sitekey: {sitekey}")

        # Получаем токен reCAPTCHA с помощью 2Captcha
        result = solver.recaptcha(sitekey=sitekey, url=url, version="v2")
        token = result["code"]
        print(f"Получен токен: {token}")

        # Вставляем токен в поле g-recaptcha-response
        captcha_response = driver.find_element(By.ID, "g-recaptcha-response")
        driver.execute_script(f"arguments[0].value = '{token}'", captcha_response)

        # Отправляем форму
        form = driver.find_element(By.TAG_NAME, "form")
        form.submit()
        print("Форма отправлена!")

        # Ждем, пока страница перезагрузится
        time.sleep(2)

        # Теперь можно продолжать парсинг данных о машине
        # (просто пример, измените его в зависимости от вашей логики)
        car_info = driver.page_source

        print("Информация о машине успешно получена!")

        with open("test.html", "w+") as file:
            file.write(car_info)

        return car_info

    except Exception as e:
        print(f"Ошибка при решении reCAPTCHA: {e}")
        driver.quit()
        return None

    finally:
        # Закрываем драйвер
        driver.quit()


get_car_info(url)
