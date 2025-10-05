import bs4
import re
import time
from typing import Dict, List

def parse_summary_info(soup: bs4.BeautifulSoup) -> Dict:
    """
    Парсит разделы 'О квартире' и 'О доме' (блоки с атрибутом data-name="OfferSummaryInfoItem")
    и извлекает из них пары "ключ-значение".
    """
    summary_data = {}

    info_items = soup.find_all('div', attrs={'data-name': 'OfferSummaryInfoItem'})
    for item in info_items:
        parts = item.find_all(['p', 'span'])
        
        if len(parts) >= 2:
            key = parts[0].text.strip()
            value = parts[1].text.strip()
            
            if key:
                summary_data[key] = value

    return summary_data

def parse_amenities(soup: bs4.BeautifulSoup) -> List:
    """
    Парсит раздел 'В квартире есть' и возвращает список удобств.
    """
    amenities_list = []
    header = soup.find(lambda tag: tag.name in ['h2'] and 'В квартире есть' in tag.text)
    
    if not header:
        return amenities_list 

    amenities_container = header.find_next_sibling('div')
    
    if not amenities_container:
        return amenities_list

    amenity_elements = amenities_container.find_all('div', class_=re.compile(r'item'))
    
    if not amenity_elements:
        amenity_elements = amenities_container.find_all('span')

    for elem in amenity_elements:
        text = elem.text.strip()
        if text: 
            amenities_list.append(text)
            
    return amenities_list

def clean_numeric_value(value_str: str) -> float:
    """
    Извлекает число из строки, удаляя единицы измерения и лишние символы.
    Преобразует запятую в точку и возвращает число.
    """
    if not isinstance(value_str, str):
        return None

    try:
        match = re.search(r'[\d,.]+', value_str)
        
        if match:
            number_str = match.group(0).replace(',', '.')
            
            return float(number_str)
            
    except (ValueError, TypeError):
        return None

    return None


class FlatPageParser:
    def __init__(self, session, url):
        self.session = session
        self.url = url

    def __load_page__(self):
        res = self.session.get(self.url)
        if res.status_code == 429:
            time.sleep(10)
        res.raise_for_status()
        self.offer_page_html = res.text
        self.offer_page_soup = bs4.BeautifulSoup(self.offer_page_html, 'html.parser')

    def __parse_flat_offer_page_json__(self):
        # Закомментированные поля либо получаем ранее из парсинга списка объявлений, либо встречаются редко
        keys_to_find = {
            "Общая площадь": "total_area",
            "Жилая площадь": "living_meters",
            "Площадь кухни": "kitchen_meters",
            # "Этаж": "floor",
            "Год постройки": "year_of_construction",
            "Ремонт": "finish_type",
            "Тип дома": "house_material_type",
            # "Мебель": "furniture",
            # "Залог": "deposit",
            # "Комиссия агенту": "commission",
            # "": "object_type"
            "Отопление": "heating_type",
            # "Планировка": "layout",
            "Парковка": "parking"
        }

        page_data = {}
        
        page_data = {k:-1 for k in keys_to_find.values()}
        page_data["phone"] = ""

        info = parse_summary_info(self.offer_page_soup)
        keys_to_clean = ['Общая площадь', 'Жилая площадь', 'Площадь кухни', 'Год постройки']

        for key in keys_to_clean:
            if key in info:
                cleaned_value = clean_numeric_value(info[key])
                info[key] = cleaned_value

        for key in info:
            if key in keys_to_find and info[key] != 'Нет информации':
                page_data[keys_to_find[key]] = info[key]
        page_data["amenities"] = parse_amenities(self.offer_page_soup)


        if "+7" in self.offer_page_html:
            page_data["phone"] = self.offer_page_html[self.offer_page_html.find("+7"): self.offer_page_html.find("+7") + 16].split('"')[0]. \
                replace(" ", ""). \
                replace("-", "")

        return page_data

    def parse_page(self):
        self.__load_page__()
        return self.__parse_flat_offer_page_json__()
