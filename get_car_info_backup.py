def get_car_info(url):
    global car_id_external

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless")
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

    # Инициализация драйвера
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    solver = TwoCaptcha("89a8f41a0641f085c8ca6e861e0fa571")

    try:
        driver.get(url)
        # check_and_handle_alert(driver)

        # Проверка на reCAPTCHA
        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")

            # Поиск iframe с reCAPTCHA
            iframe = driver.find_element(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
            iframe_src = iframe.get_attribute("src")
            print(f"Iframe src: {iframe_src}")

            # Извлечение sitekey из параметра 'k' в URL iframe
            match = re.search(r"[?&]k=([^&]+)", iframe_src)
            if not match:
                print("Sitekey не найден в iframe URL.")
                driver.quit()
                exit()

            sitekey = match.group(1)
            print(f"Sitekey: {sitekey}")

            # Решение reCAPTCHA через 2Captcha
            try:
                result = solver.recaptcha(
                    sitekey=sitekey, url=driver.current_url, version="v2"
                )
                token = result["code"]
                print("Токен reCAPTCHA успешно получен.")
            except Exception as e:
                print(f"Ошибка при решении reCAPTCHA: {e}")
                driver.quit()
                exit()

            # Возврат в основной контекст страницы
            driver.switch_to.default_content()

            # Вставка токена в textarea элемента g-recaptcha-response
            captcha_response = driver.find_element(
                By.CSS_SELECTOR, ".g-recaptcha-response"
            )
            driver.execute_script(
                "arguments[0].style.display = 'block';", captcha_response
            )

            print(captcha_response.get_property("value"))

            driver.execute_script(f"arguments[0].value = '{token}';", captcha_response)
            print("Токен вставлен в g-recaptcha-response.")

            # Отправка формы
            try:
                form = driver.find_element(By.CSS_SELECTOR, "form.cont_main_captcha")
                form.submit()
                print("Форма успешно отправлена.")
            except Exception as e:
                print(f"Ошибка при отправке формы: {e}")
                driver.quit()
                exit()

            # Ожидание завершения процесса и обновления страницы
            time.sleep(5)

            # Получение страницы с информацией о машине
            car_info = driver.page_source
            print("Информация о машине успешно получена!")
            # print(car_info)

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        # Проверка элемента areaLeaseRent
        try:
            print("Поиск areaLeaseRent")
            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                logging.info("Данная машина находится в лизинге.")
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            logging.warning("Элемент areaLeaseRent не найден.")

        # Инициализация переменных
        car_title, car_date, car_engine_displacement, car_price = "", "", "", ""

        meta_elements = driver.find_elements(By.CSS_SELECTOR, "meta[name^='WT.']")
        meta_data = {}
        for meta in meta_elements:
            name = meta.get_attribute("name")
            content = meta.get_attribute("content")
            meta_data[name] = content

        car_date = f'01{meta_data["WT.z_month"]}{meta_data["WT.z_year"][-2:]}'
        car_price = meta_data["WT.z_price"]

        # Ищем объём двигателя
        try:
            # Найти элемент с id "dsp"
            dsp_element = driver.find_element(By.ID, "dsp")
            # Получить значение из атрибута "value"
            car_engine_displacement = dsp_element.get_attribute("value")
        except Exception as e:
            print(f"Ошибка при получении объема двигателя: {e}")

        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={car_price}&date={car_date}&volume={car_engine_displacement}"
        print(f"Данные о машине получены: {new_url}, {car_title}")

        return [new_url, car_title]

    except Exception as e:
        logging.error(f"Произошла ошибка: {e}")
        return None, None

    finally:
        driver.quit()
