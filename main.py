import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
import json

category_lst = []
pagen_lst = []
domain = 'https://parsinger.ru/html/'
data_dict = {}  # Словарь для хранения данных о товарах по категориям


def get_soup(url):
    """
    Получает HTML-код страницы и возвращает его в виде объекта BeautifulSoup.

    Параметры:
    url (str): URL-адрес страницы, которую нужно получить.

    Возвращает:
    BeautifulSoup: Объект BeautifulSoup, представляющий HTML-код страницы.
    """
    resp = requests.get(url=url)
    return BeautifulSoup(resp.text, 'lxml')


def get_urls_categories(soup):
    """
    Извлекает URL-адреса категорий из переданного объекта BeautifulSoup 
    и добавляет их в список category_lst.

    Параметры:
    soup (BeautifulSoup): Объект BeautifulSoup, представляющий HTML-код страницы с категориями.
    """
    all_link = soup.find('div', class_='nav_menu').find_all('a')
    for cat in all_link:
        category_lst.append(domain + cat['href'])


def get_urls_pages(category_lst):
    """
    Извлекает URL-адреса страниц товаров для каждой категории 
    и добавляет их в список pagen_lst.

    Параметры:
    category_lst (list): Список URL-адресов категорий.
    """
    for cat in category_lst:
        resp = requests.get(url=cat)
        soup = BeautifulSoup(resp.text, 'lxml')
        for pagen in soup.find('div', class_='pagen').find_all('a'):
            pagen_lst.append(domain + pagen['href'])


async def get_data(session, link, category_name):
    """
    Асинхронно получает данные о товарах с указанной страницы 
    и добавляет их в словарь data_dict по соответствующей категории.

    Параметры:
    session (aiohttp.ClientSession): Асинхронная сессия для выполнения HTTP-запросов.
    link (str): URL-адрес страницы товаров.
    category_name (str): Название категории, к которой относятся товары.
    """
    async with session.get(link) as response:
        if response.ok:
            resp = await response.text()
            soup = BeautifulSoup(resp, 'lxml')
            item_card = [x['href'] for x in soup.find_all('a', class_='name_item')]
            for x in item_card:
                url2 = domain + x
                async with session.get(url=url2) as response2:
                    resp2 = await response2.text()
                    soup2 = BeautifulSoup(resp2, 'lxml')
                    name = soup2.find('p', id='p_header').text.strip()
                    article = soup2.find('p', class_='article').text.strip() if soup2.find('p', class_='article') else None
                    old_price = int(soup2.find('span', id='old_price').text.split(" ")[0])
                    price = int(soup2.find('span', id='price').text.split(" ")[0])
                    in_stock = int(soup2.find('span', id='in_stock').text.split(":")[1])
                    description_items = {li.text.strip().split(': ')[0]: li.text.strip().split(': ')[1] for li in soup2.find('ul', id='description').find_all('li')}
                    
                    # Создаем словарь для хранения данных о товаре
                    product_data = {
                        'Название': name,
                        'Артикуль': article,
                        'Цена': price,
                        'Старая цена': old_price,
                        'В наличие': in_stock,
                        'Описание': description_items
                    }

                    # Добавляем данные в словарь по категории
                    if category_name not in data_dict:
                        data_dict[category_name] = []
                    data_dict[category_name].append(product_data)  # Добавляем данные о товаре в категорию


async def main():
    """
    Основная асинхронная функция, которая управляет процессом 
    получения данных о товарах и их сохранения в JSON файл.
    """
    async with aiohttp.ClientSession() as session:
        tasks = []
        for cat in category_lst:
            category_name = cat.split('/')[-1]  # Получаем название категории из URL
            resp = requests.get(cat)
            soup = BeautifulSoup(resp.text, 'lxml')
            pages = [domain + pagen['href'] for pagen in soup.find('div', class_='pagen').find_all('a')]

            for link in pages:
                task = asyncio.create_task(get_data(session, link, category_name))
                tasks.append(task)

        await asyncio.gather(*tasks)
    
    # Сохраняем данные в JSON файл
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=4)


url = 'https://parsinger.ru/html/index1_page_1.html'
soup = get_soup(url)
get_urls_categories(soup)
get_urls_pages(category_lst)

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
