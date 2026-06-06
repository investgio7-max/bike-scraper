"""
Утилиты для парсинга информации о велосипедах
"""

import re
from typing import Optional, Dict
from config import BIKE_BRANDS, BIKE_GROUPSETS, BIKE_TYPES
from utils_logger import get_logger

logger = get_logger(__name__)


class BikeParser:
    """Парсер для извлечения информации о велосипеде из текста"""

    @staticmethod
    def extract_brand(text: str) -> Optional[str]:
        """Извлечь бренд из текста"""
        if not text:
            return None

        text_lower = text.lower()

        for brand in BIKE_BRANDS:
            if brand.lower() in text_lower:
                return brand

        return None

    @staticmethod
    def extract_frame_size(text: str) -> Optional[str]:
        """Извлечь размер рамы"""
        if not text:
            return None

        # Размеры в см
        cm_match = re.search(r'(\d{2,3})\s*cm', text, re.IGNORECASE)
        if cm_match:
            return f"{cm_match.group(1)}cm"

        # Размеры S, M, L, XL
        size_match = re.search(r'\b([XS]{0,2}[ML]|S|M|L|XL)\b', text, re.IGNORECASE)
        if size_match:
            return size_match.group(1).upper()

        # Дюймы
        inches_match = re.search(r"(\d{2})\s*['\"]", text)
        if inches_match:
            return f"{inches_match.group(1)}\""

        return None

    @staticmethod
    def extract_groupset(text: str) -> Optional[str]:
        """Извлечь группсет"""
        if not text:
            return None

        text_lower = text.lower()

        for groupset in BIKE_GROUPSETS:
            if groupset.lower() in text_lower:
                # Проверяем версию (если есть)
                version_match = re.search(
                    rf'{groupset.lower()}\s+(\d+|di2|mechanical)',
                    text_lower
                )
                if version_match:
                    return f"{groupset} {version_match.group(1)}"
                return groupset

        return None

    @staticmethod
    def extract_bike_type(text: str) -> Optional[str]:
        """Извлечь тип велосипеда"""
        if not text:
            return None

        text_lower = text.lower()

        for bike_type in BIKE_TYPES:
            if bike_type.lower() in text_lower:
                return bike_type

        # Если не найдено, пробуем по ключевым словам
        if 'carretera' in text_lower or 'road' in text_lower:
            return 'road bike'
        elif 'grava' in text_lower or 'gravel' in text_lower:
            return 'gravel bike'
        elif 'ciclocross' in text_lower or 'cyclocross' in text_lower:
            return 'cyclocross'

        return None

    @staticmethod
    def extract_year(text: str) -> Optional[int]:
        """Извлечь год выпуска"""
        if not text:
            return None

        # Ищем 4-значное число в диапазоне 2000-2025
        years = re.findall(r'\b(20[0-2]\d)\b', text)

        if years:
            # Берем самое свежее
            return max(int(year) for year in years)

        return None

    @staticmethod
    def extract_weight(text: str) -> Optional[float]:
        """Извлечь вес велосипеда"""
        if not text:
            return None

        # Вес в килограммах
        match = re.search(r'(\d{1,2}[.,]\d{1,2})\s*kg', text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', '.'))

        # Вес в фунтах
        match = re.search(r'(\d{2,3})\s*(lbs|pounds|lb)', text, re.IGNORECASE)
        if match:
            lbs = float(match.group(1))
            return round(lbs / 2.205, 2)  # Преобразуем в кг

        return None

    @staticmethod
    def extract_frame_material(text: str) -> Optional[str]:
        """Извлечь материал рамы"""
        if not text:
            return None

        text_lower = text.lower()

        materials = {
            'carbon': ['carbon', 'carbón', 'cf'],
            'aluminum': ['aluminum', 'aluminium', 'alu', 'aluminio'],
            'steel': ['steel', 'acero'],
            'titanium': ['titanium', 'titanio', 'ti']
        }

        for material, keywords in materials.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return material

        return None

    @staticmethod
    def extract_color(text: str) -> Optional[str]:
        """Извлечь цвет велосипеда"""
        if not text:
            return None

        colors = [
            'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'gray', 'silver',
            'negro', 'blanco', 'rojo', 'azul', 'verde', 'amarillo', 'naranja', 'gris', 'plateado',
            'carbon', 'matte', 'glossy'
        ]

        text_lower = text.lower()

        for color in colors:
            if color in text_lower:
                return color.capitalize()

        return None

    @staticmethod
    def extract_condition(text: str) -> Optional[str]:
        """Извлечь состояние велосипеда"""
        if not text:
            return None

        text_lower = text.lower()

        conditions = {
            'new': ['new', 'nuevo', 'sin usar', 'nunca usado'],
            'like_new': ['como nuevo', 'like new', 'mint condition', 'prácticamente nuevo'],
            'good': ['buen estado', 'good condition', 'bien cuidado', 'en buen estado'],
            'fair': ['algo gastado', 'fair condition', 'necesita reparación', 'necesita limpieza']
        }

        for condition, keywords in conditions.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return condition

        return None

    @classmethod
    def parse_listing(cls, title: str, description: str = '') -> Dict:
        """
        Парсить объявление и извлечь информацию о велосипеде
        """
        full_text = f"{title} {description}"

        return {
            'brand': cls.extract_brand(full_text),
            'frame_size': cls.extract_frame_size(full_text),
            'groupset': cls.extract_groupset(full_text),
            'bike_type': cls.extract_bike_type(full_text),
            'year': cls.extract_year(full_text),
            'weight': cls.extract_weight(full_text),
            'frame_material': cls.extract_frame_material(full_text),
            'color': cls.extract_color(full_text),
            'condition': cls.extract_condition(full_text),
        }


def normalize_price(price_text: str) -> Optional[float]:
    """Нормализовать цену"""
    if not price_text:
        return None

    # Удаляем символы валют и пробелы
    clean = re.sub(r'[^\d.,]', '', str(price_text)).strip()

    # Берем первое число
    match = re.search(r'(\d+[.,]?\d*)', clean)
    if match:
        return float(match.group(1).replace(',', '.'))

    return None


def parse_location(location_text: str) -> tuple[Optional[str], str]:
    """
    Парсить локацию и возвращать (город, страна)
    """
    if not location_text:
        return None, 'Spain'

    # Предполагаем, что это Испания
    return location_text.strip(), 'Spain'
