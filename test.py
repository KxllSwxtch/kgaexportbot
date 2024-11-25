import requests
import re
from bs4 import BeautifulSoup
from twocaptcha import TwoCaptcha


def get_sitekey(url):
    # Отправляем GET-запрос к странице
    response = requests.get(url)

    # Если запрос успешен
    if response.status_code == 200:
        # Ищем sitekey в JavaScript-коде с помощью регулярного выражения
        match = re.search(r"grecaptcha.execute\('([a-zA-Z0-9_-]+)',", response.text)

        if match:
            # Извлекаем sitekey
            sitekey = match.group(1)
            return sitekey
        else:
            raise Exception("Не удалось найти sitekey на странице.")
    else:
        raise Exception(f"Ошибка при запросе страницы: {response.status_code}")


solver = TwoCaptcha("89a8f41a0641f085c8ca6e861e0fa571")

proxies = {
    "http": "http://B01vby:GBno0x@45.118.250.2:8000",
    "https": "http://B01vby:GBno0x@45.118.250.2:8000",
}

url = "http://www.encar.com/dc/dc_cardetailview.do?pageid=fc_carsearch&listAdvType=word&carid=37737638"


def get_ip():
    response = requests.get(
        "https://api.ipify.org?format=json", proxies=proxies, verify=False
    )
    ip = response.json()["ip"]
    print(f"Current IP address: {ip}")
    return ip


print(get_ip())


response = requests.get(
    url,
    proxies=proxies,
    verify=False,
)


# Если на странице есть reCAPTCHA
if "grecaptcha" in response.text:
    sitekey = get_sitekey(url)  # Извлекаем sitekey

    # Решаем reCAPTCHA с использованием 2Captcha
    result = solver.recaptcha(sitekey=sitekey, url=url, version="v3", score=0.9)
    token = result["code"]

    # Отправка токена на сервер
    validation_url = "http://www.encar.com/validation_recaptcha.do?method=v3"
    data = {"token": token}

    # Отправляем POST-запрос для верификации reCAPTCHA
    validation_response = requests.post(validation_url, data=data, proxies=proxies)

    print("\n\n")
    print(validation_response.text)
    print("\n\n")

    # Проверка ответа
    if validation_response.status_code == 200:
        validation_result = validation_response.json()
        if validation_result[0]["success"]:
            print("reCAPTCHA прошла успешно.")
        else:
            print("reCAPTCHA не пройдена.")
    else:
        print(
            f"Ошибка при отправке запроса на верификацию reCAPTCHA: {validation_response.status_code}"
        )
else:
    print("reCAPTCHA не найдена на странице.")
