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

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    load_cookies(driver)

    try:
        driver.get(url)
        check_and_handle_alert(driver)

        if "reCAPTCHA" in driver.page_source:
            print("Обнаружена reCAPTCHA. Пытаемся решить...")
            check_and_handle_alert(driver)
            driver.refresh()

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

        # Сохранение куки после успешного решения reCAPTCHA или загрузки страницы
        save_cookies(driver)

        # Парсим URL для получения carid
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        car_id = query_params.get("carid", [None])[0]
        car_id_external = car_id

        # Проверка элемента areaLeaseRent на наличие лизинга
        try:
            lease_area = driver.find_element(By.ID, "areaLeaseRent")
            title_element = lease_area.find_element(By.CLASS_NAME, "title")

            if "리스정보" in title_element.text or "렌트정보" in title_element.text:
                return [
                    "",
                    "Данная машина находится в лизинге. Свяжитесь с менеджером.",
                ]
        except NoSuchElementException:
            print("Элемент areaLeaseRent не найден или нет информации о лизинге.")

        # Инициализация переменных для информации о машине
        car_title = ""
        car_date = ""
        car_engine_capacity = ""
        car_price = ""

        # Проверка элемента product_left
        try:
            product_left = driver.find_element(By.CLASS_NAME, "product_left")
            product_left_splitted = product_left.text.split("\n")

            prod_name = product_left.find_element(By.CLASS_NAME, "prod_name")

            car_title = prod_name.text.strip()
            car_date = product_left_splitted[3]
            car_engine_capacity = product_left_splitted[6]
            car_price = re.sub(r"\D", "", product_left_splitted[1])

            formatted_price = car_price.replace(",", "")
            formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]
            cleaned_date = "".join(filter(str.isdigit, car_date))
            formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

            # Создание URL для передачи данных
            new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"
            return [new_url, car_title]

        except NoSuchElementException:
            print("Элемент product_left не найден. Переходим к gallery_photo.")

            try:
                gallery_element = driver.find_element(
                    By.CSS_SELECTOR, "div.gallery_photo"
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

        # Форматирование значений для URL
        formatted_price = car_price.replace(",", "")
        formatted_engine_capacity = car_engine_capacity.replace(",", "")[0:-2]
        cleaned_date = "".join(filter(str.isdigit, car_date))
        formatted_date = f"01{cleaned_date[2:4]}{cleaned_date[:2]}"

        # Конечный URL
        new_url = f"https://plugin-back-versusm.amvera.io/car-ab-korea/{car_id}?price={formatted_price}&date={formatted_date}&volume={formatted_engine_capacity}"

        return [new_url, car_title]

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None, None

    finally:
        # Обработка всплывающих окон (alerts)
        try:
            alert = driver.switch_to.alert
            alert.dismiss()  # Или alert.dismiss(), если хотите закрыть alert
        except NoAlertPresentException:
            print("Нет активного всплывающего окна.")
        except Exception as alert_exception:
            print(f"Ошибка при обработке alert: {alert_exception}")

        driver.quit()
