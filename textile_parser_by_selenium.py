from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver import Keys
import json
import traceback
import schedule
import time
from fake_useragent import UserAgent

# Скрипт парсит сайт textile.by посредством библиотеки Selenium и полностью соответствует ТЗ заказчика

ua = UserAgent(browsers='Chrome', os='Linux', platforms='desktop', fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0')
print(ua.random)


def remove_cookies(cookies, url):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = 'eager'
    options.add_argument(f'user-agent={ua.random}')
    with webdriver.Chrome(options=options) as browser:
        browser.get(url)
        if len(cookies) > 0:
            try:
                browser.find_element(By.ID, 'cclose').click()
            except Exception:
                pass
        else:
            pass


def lets_parse(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.page_load_strategy = 'eager'
    options.add_argument(f'user-agent={ua.random}')
    with webdriver.Chrome(options=options) as browser:
        browser.get(url)
        browser.set_page_load_timeout(10)
        time.sleep(10)
        browser.delete_all_cookies()
        actions = ActionChains(browser)

        final_list = []
        # Прокручиваем стартовую страницу вниз, чтобы избавиться от "липкого" header'а и собрать ссылки на категории товаров:
        body = browser.find_element(By.TAG_NAME, 'body')
        body.send_keys(Keys.ARROW_DOWN)
        categories = browser.find_elements(By.CLASS_NAME, 'banner')
        links = [i.find_element(By.TAG_NAME, 'a').get_attribute('href') for i in categories]

        for link in links:
            # Открываем каждую ссылку отдельно в цикле:
            browser.get(link)
            # Закрываем окно cookies:
            cookies = browser.find_elements(By.ID, 'cookie')
            remove_cookies(cookies, url)
            # Собираем ссылки на товары, избегая дубликатов:
            products = set()
            while True:
                container = browser.find_element(By.CLASS_NAME, 'row.row-c')
                browser.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", container)

                # Попутно собираем типы товаров, чтобы потом уложить в итоговый файл:
                type = browser.find_element(By.CLASS_NAME, 'col-sm-5').text
                products.update([i.get_attribute('href') for i in browser.find_element(By.CLASS_NAME, 'row.row-c').find_elements(By.CSS_SELECTOR, "[data-hpm-href='1']")])

                # Пагинация - заходим на следующую страницу, если она есть:
                next = (By.CLASS_NAME, 'fa.fa-caret-right')
                next_ = browser.find_elements(By.CLASS_NAME, 'fa.fa-caret-right')
                if len(next_) > 0:
                    browser.execute_script("return arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_[0])
                    WebDriverWait(browser, 10).until(EC.visibility_of_element_located(next))
                    actions.scroll_to_element(next_[0]).perform()
                    browser.execute_script("arguments[0].click();", next_[0])
                    continue
                else:
                    break
                # Заходим на страницу товара:
            for product in products:
                browser.get(product)

                # Закрываем окно cookies:
                cookies = browser.find_elements(By.ID, 'cookie')
                remove_cookies(cookies, url)

                # Собираем данные со страницы:
                product_dict = {}
                cats = ['УНИСЕКС', 'МУЖСК', 'ЖЕНСК', 'ДЕТСК']
                product_dict['Артикул товара'] = browser.find_element(By.CLASS_NAME, 'model').text
                product_dict['URL страницы'] = product
                product_dict['Стоимость'] = float(browser.find_element(By.CLASS_NAME, 'price').text[:2])
                product_dict['Производитель'] = browser.find_element(By.CLASS_NAME, 'manufacturer').text
                product_dict['Тип товара'] = type
                name = browser.find_element(By.CLASS_NAME, 'name-block').find_element(By.TAG_NAME, "h1").text
                for i in cats:
                    if i in name:
                        product_dict['Категория'] = i
                product_dict['Заголовок'] = name
                print('Парсим товар ', name)

                # Собираем данные о цветах товара, а для каждого цвета - ссылка на изображение, имеющиеся размеры,
                # остатки по размерам, суммарный остаток по этому цвету и наценки для больших размеров:
                colors = browser.find_elements(By.CLASS_NAME, 'hpm-v-image')
                if len(colors) > 0:
                # Словарь для цветов и характеристик каждого цвета:
                    color_dict = {}
                    for color in range(len(colors)):
                    # Словарь для характеристик каждого отдельного цвета:
                        sizes_dict = {}
                        try:
                        # Дожидаемся видимости контейнера со ссылками на цвета:
                            container = browser.find_element(By.CLASS_NAME, 'hpmodel_type_images.hpm-type-images')
                            WebDriverWait(browser, 10).until(EC.visibility_of(container))
                            col = browser.find_elements(By.CLASS_NAME, 'hpm-v-image')[color]

                            # Находим все цвета по порядку:
                            img = col.find_element(By.TAG_NAME, 'img')

                            # Перемещаем фокус в зону видимости ссылки на цвет:
                            browser.execute_script("return arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});", img)

                            # Ссылка на контейнер с параметрами для предыдущего цвета здесь используется как якорь для начала сбора информации:
                            browser.implicitly_wait(0.5)
                            old_sizes = browser.find_elements(By.CLASS_NAME, 'zak-options')

                            # Перемещаемся на ссылку цвета, дожидаемся ее кликабельности и кликаем
                            actions.move_to_element(img).perform()
                            WebDriverWait(browser, 10).until(EC.element_to_be_clickable(img))
                            browser.execute_script("arguments[0].click();", img)

                            # Проверяем, устарел ли предыдущий блок с информацией:
                            if len(old_sizes) > 0:
                                WebDriverWait(browser, 10).until(EC.staleness_of(old_sizes[0]))

                            # Если да, то получаем блок заново:
                                sizes_ = browser.find_elements(By.CLASS_NAME, 'zak-options')

                                # Проверяем, получили мы блок или нет. Если нет, в словарь собираем только название цвета и ссылку на изображение товара:
                            if len(sizes_) > 0:
                                browser.execute_script("return arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});",sizes_[0])
                                color_name = browser.find_elements(By.CLASS_NAME, 'hpm-v-image')[color]
                                sizes_dict['URL изображения'] = color_name.find_element(By.TAG_NAME, 'img').get_attribute('src')
                                sizes_dict['Размеры'] = [i.text for i in sizes_[0].find_elements(By.CLASS_NAME, 'mname.col-xs-2')]
                                balance = [int(num.get_attribute('max')) for num in sizes_[0].find_elements(By.CLASS_NAME, 'owq-input')]
                                sizes_dict['Остаток на складе'] = balance
                                sizes_dict['Общий остаток'] = sum(balance)
                                markup = sizes_[0].find_elements(By.CLASS_NAME, 'mprice')
                                if len(markup) > 0:
                                    sizes_dict['Наценки'] = [float(i.text[1:-3]) for i in markup]
                                color_dict[str(color+1)+"_"+color_name.find_element(By.TAG_NAME, 'img').get_attribute('alt')] = sizes_dict
                        except Exception as e:
                            print(traceback.format_exc())
                            continue
                    product_dict['Цвета'] = color_dict

                # Если у товара нет вариантов расцветок, собираем ту же информацию без привязки к цветам:
                else:
                    sizes_dict_ = {}
                    sizes_ = browser.find_element(By.CLASS_NAME, 'zak-options')
                    browser.execute_script("return arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});",
                                       sizes_)
                    WebDriverWait(browser, 10).until(EC.visibility_of(sizes_))
                    sizes_dict_['Размеры'] = [i.text for i in sizes_.find_elements(By.CLASS_NAME, 'mname.col-xs-2')]
                    bal = browser.find_elements(By.CLASS_NAME, 'owq-input')
                    store = [int(num.get_attribute('max')) for num in bal]
                    sizes_dict_['Остаток на складе'] = store
                    sizes_dict_['Общий остаток'] = sum(store)
                    mark = browser.find_elements(By.CLASS_NAME, 'mprice')
                    if len(mark) > 0:
                        sizes_dict_['Наценки'] = [float(i.text[1:-3]) for i in mark]
                    product_dict['Размеры'] = sizes_dict_
                try:
                # Собираем описание, удаляя из текста лишние знаки:
                    descript = browser.find_element(By.CLASS_NAME, 'col-sm-8')
                    browser.execute_script("return arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});",descript)
                    WebDriverWait(browser, 10).until(EC.visibility_of(descript))
                    product_dict['Описание'] = descript.text.replace('\u200b\u200bв', '').replace('\n', '').replace('Брошюра производителя', '')
                except Exception:
                    continue
                chars = browser.find_elements(By.CSS_SELECTOR, 'li.attr')

                # Закрываем окно cookies:
                cookies = browser.find_elements(By.ID, 'cookie')
                remove_cookies(cookies, url)

                # Копируем в словарь таблицу с характеристиками товара:
                if len(chars) > 0:
                    title = chars[0].find_element(By.TAG_NAME, 'span')
                    browser.execute_script("return arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});",title)
                    WebDriverWait(browser, 20).until(EC.visibility_of(title))
                    browser.execute_script("arguments[0].click();", title)
                    try:
                        table = browser.find_element(By.CLASS_NAME, 'table.attribute1')
                        browser.execute_script("return arguments[0].scrollIntoView({behavior: 'auto', block: 'center'});",table)
                        WebDriverWait(browser, 20).until(EC.visibility_of(table))
                        header = [td.find_element(By.TAG_NAME, 'td').text for td in table.find_elements(By.TAG_NAME, 'tr')][1:]
                        values = [td.find_elements(By.TAG_NAME, 'td')[1].text for td in table.find_elements(By.TAG_NAME, 'tr')[1:]]
                        characteristics = dict(zip(header, values))
                    except Exception:
                        continue
                product_dict['Характеристики'] = characteristics

                # Добавляем полученный словарь в общий список:
                final_list.append(product_dict)

        return final_list


url = 'https://textile.by'

# Скрипт будет отрабатывать каждые 10 ч:

schedule.every(10).hours.do(lets_parse, url)
data = lets_parse(url)

# Запись полученной структуры в JSON-файл:

with open('textile_by_selenium.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

