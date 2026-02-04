import requests
from bs4 import BeautifulSoup
import re
from random import choice
import traceback
import json
import schedule
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure


# Заголовки для входа на сайт:

desktop_agents = ['Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1 Safari/602.2.14',
                 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
                 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
                 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36',
                 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
                 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
                 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0']


def random_headers():
    return {'User-Agent': choice(desktop_agents), 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'}

# Получение основной страницы:


def parse(url):

    response=requests.get(url=url, headers=random_headers())
    soup=BeautifulSoup(response.text, 'html.parser')

    container_divs=soup.find_all('div', class_=re.compile('banner banner'))
    names=soup.select('div.b-info')

# Сбор ссылок для категорий товаров:

    links=[url[:-1]+div.find('a')['href'] for div in container_divs]
    dict_url=dict.fromkeys(links, [])

# Сбор категорий товаров:

    name=[i.find('a').get_text(strip=True) for i in names]
    final_dict=dict.fromkeys(name, {})

# Сбор ссылок для товаров в категориях:

    for link in links:
        try:
            page_response=requests.get(link)
            page_soup=BeautifulSoup(page_response.text, 'html.parser')
            special_link=page_soup.find_all('div', class_='image')
            new_link=[element.find('a')['href'] for element in special_link]
            dict_url[link]=new_link
        except requests.exceptions.RequestException as e:
            print(f'Ошибка при запросе {url}: {e}')

# Подсчет количества ссылок на товары:

    count_urls=sum([len(value) for key, value in dict_url.items()])
    page_num=0

# Получение характеристик товаров и итогового словаря со значениями:
    final_dict=[]
    for key, value in dict_url.items():
        while page_num<=count_urls:
            for i in value:
                tov_url=requests.get(i, headers=random_headers()) # Получение ссылки на страницу товара с характеристиками
                tov=BeautifulSoup(tov_url.text, 'html.parser')

                characteristics_1=tov.find('div', class_='col-sm-5') # Контейнер с основными характеристиками товара
                characteristics_2=tov.find('ul', class_='breadcrumb') # Контейнер с категорией товара
                characteristics_3=tov.find('div', class_='col-sm-8') # Контейнер с описанием товара
                try:
                    """
                    Сбор характеристик товаров, значение переменных:
                    characteristics_dict = Словарь с характеристиками каждого товара
                    art = Артикул товара
                    price = Цена товара
                    man = Наименование производителя
                    head = Наименование товара
                    hashes = Контейнер со списком вариантов расцветок товара
                    color = Тег с расцветками и ссылками на изображения товара в разных расцветках
                    colors = Список наименований расцветок товара
                    color_pics = Словарь с наименованиями расцветок и ссылками на изображения товара в данных расцветках
                    size = Словарь с размерами, остатками товара на складе и наценками на определенные размеры
                    type = Тип товара (головные уборы, брюки и т. п.)
                    categories = Категория товара (мужское, женское, детское, унисекс)
                    description = Описание товара
                    """
                    characteristics_dict = {}
                    art=characteristics_1.select_one('.model').get_text(separator=' ', strip=True)
                    price=characteristics_1.find('ul', class_='list-inline').find_all('li')[0].get_text(strip=True)[:-2]
                    man=characteristics_1.find('a', class_='manufacturer').get_text(strip=True)
                    head=''.join(characteristics_1.find('h1').text).replace('\n', '').replace('\xa0', '')
                    hashes=characteristics_1.find('div', class_='hpmodel_type_images hpm-type-images')
                    type=characteristics_2.select('li')[1].get_text(strip=True)
                    characteristics_dict['Артикул товара']=re.sub(r'\s+', ' ', art).strip()
                    characteristics_dict['URL страницы']=i
                    characteristics_dict['Стоимость']=float(price)
                    characteristics_dict['Производитель']=man
                    characteristics_dict['Тип']=type
                    categories_=characteristics_2.find_all('li')
                    if len(categories_)>=3:
                        characteristics_dict['Категория']=categories_[2].get_text(strip=True).replace('\xa0', '')
                    else:
                        characteristics_dict['Категория']='унисекс'
                    characteristics_dict['Заголовок']=re.sub(r'\s+', ' ', head).strip()
                    if hashes:
                    # Получение списка цветов товара:
                        color=hashes.find_all('img')
                        colors=[i.get('alt') for i in color]
                        pics=[e.get('src') for e in color]
                        color_pics=dict(zip(colors, pics))
                        characteristics_dict['Цвета']=color_pics
                    else:
                    # Получение списка для остатков на складе, размеров и наценок в случае, если товар не имеет разных вариантов расцветок:
                        no_col={}
                        sizes=characteristics_1.find('div', class_='zak-options')
                        if sizes:
                            """
                            Список переменных:
                            size = Список размеров
                            norm_balance = Остаток на складе для каждого размера
                            sum_bal = Суммарный остаток
                            markup = Наценки для больших размеров
                            """
                            size=[i.get_text(strip=True) for i in sizes.find_all('div', class_='mname col-xs-2')]
                            balance=sizes.find_all('div', class_=re.compile(r'mcount'))
                            markup=[i.get_text(strip=True) for i in sizes.find_all('span', class_='mprice')]
                            digit = [char.find('input').next_sibling.get_text(strip=True)[24:] for char in balance]
                            sum_bal=[float(x) for x in ' '.join(digit).split() if x.isnumeric()]
                            norm_balance=''.join(digit).split('.')
                            del norm_balance[-1]

                            no_col['Размеры']=size
                            no_col['Общий остаток']=sum(sum_bal)
                            no_col['Остаток на скаде для каждого размера']=norm_balance
                            no_col['Наценки для больших размеров']=markup

                            characteristics_dict['Размеры']=no_col
                    if characteristics_3:
                        description=characteristics_3.get_text(separator='', strip=True).replace('\xa0', '')
                        characteristics_dict['Описание']=description.replace('\u200b\u200bв', '')
                    else:
                        characteristics_dict['Описание'] = []

#                    if characteristics_dict not in final_dict:
                    final_dict.append(characteristics_dict)

                    page_num+=1
                    print(f'Номер страницы: {page_num}')
                    continue
                except Exception as e:
                    print(f'Ошибка при запросе {cat_url}: {e}')
                    print(traceback.format_exc())
                    page_num+=1
                    continue
            break
    return final_dict

url='https://textile.by/'

# Настройка запуска парсера через каждые 5 часов:

schedule.every(5).hours.do(parse, url)
data=parse(url)
print(f'Всего: {len(data)}')
# Формирование файла JSON с результатами:

with open('textile.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

mongo_url = "mongodb://localhost:27017"
db_name = "textile_data"
collection = "textile_products"

try:
    with MongoClient(mongo_url) as client:
        client.admin.command('ping')
        db = client[db_name]
        collection = db[collection]
        print(f'До удаления: {collection.count_documents({})}')
        deletion = collection.delete_many({})
        print(f'Удалено: {deletion.deleted_count}')
        print(f'После удаления: {collection.count_documents({})}')
        inserted = collection.insert_many(data)
        print(f'вставлено: {len(inserted.inserted_ids)}')
        client.close()
except ConnectionFailure:
    print('Ошибка подключения')
except OperationFailure as e:
    print(f'Ошибка операции с базой данных {e}')
except Exception as e:
    print(f'Ошибка {e}')
    print(traceback.format_exc())