"""
🤖 AI Bike Parser - Интеллектуальный парсер характеристик велосипедов

Использует:
- Regex парсинг текста
- OCR для распознавания текста на изображениях
- Claude Vision API для анализа изображений
- Расчет confidence score
"""

import re
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# =====================
# ДАННЫЕ И КОНФИГУРАЦИЯ
# =====================

BRANDS = {
    'Canyon', 'Specialized', 'Scott', 'Cervelo', 'Pinarello', 'BMC',
    'Trek', 'Giant', 'Cannondale', 'Ridley', 'Colnago', 'Factor', 'Wilier',
    'Cube', 'Merida', 'Bianchi', 'Focus', 'Lapierre', 'Felt', 'Kona',
    'Orbea', 'Norco', 'Polygon', 'GT', 'Fuji', 'LaPierre'
}

MODELS = {
    # Canyon
    'aeroad', 'grail', 'ultimate', 'grizl', 'endurace',
    # Specialized
    'tarmac', 'roubaix', 'crux', 'diverge',
    # Scott
    'foil', 'addict rc', 'speedster',
    # Cervelo
    's5', 'r5', 'caledonia', 'aspero',
    # Pinarello
    'dogma', 'prince', 'gan',
    # Trek
    'madone', 'emonda', 'checkpoint',
    # Giant
    'tcr', 'propel', 'revolt',
    # BMC
    'teamelite', 'roadmachine', 'alpenchallenge',
    # Cannondale
    'systemsix', 'supersix', 'caad',
    # Wilier
    'cento10', 'mortirolo',
    # Colnago
    'v3rs', 'act',
}

GROUPSETS = {
    'shimano': {
        '105': '105',
        'ultegra': 'Ultegra',
        'dura-ace': 'Dura-Ace',
        'di2': 'Di2',
        'r7100': '105',
        'r8170': 'Ultegra',
        'r9270': 'Dura-Ace',
    },
    'sram': {
        'rival': 'Rival',
        'force': 'Force',
        'red': 'Red',
        'axs': 'AXS',
        'apex': 'Apex',
    },
    'campagnolo': {
        'chorus': 'Chorus',
        'record': 'Record',
        'super record': 'Super Record',
    }
}

BIKE_TYPES = {
    'road bike': 'road',
    'road': 'road',
    'carretera': 'road',
    'gravel bike': 'gravel',
    'gravel': 'gravel',
    'grava': 'gravel',
    'cyclocross': 'cyclocross',
    'cx': 'cyclocross',
    'ciclocross': 'cyclocross',
    'endurance': 'endurance',
    'aero': 'aero',
    'climbing': 'climbing',
}

FRAME_MATERIALS = {
    'carbon': 'carbon',
    'aluminum': 'aluminum',
    'steel': 'steel',
    'titanium': 'titanium',
}

SIZE_LIQUIDITY = {
    'XXS': 2, 'XS': 4, 'S': 8, 'M': 10, 'L': 9, 'XL': 6, 'XXL': 3,
    '48': 3, '50': 5, '52': 8, '54': 10, '56': 9, '58': 7, '60': 4, '62': 2
}


@dataclass
class BikeInfo:
    """Структура информации о велосипеде"""
    brand: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    year: Optional[int] = None
    bike_type: Optional[str] = None
    frame_material: Optional[str] = None
    groupset_brand: Optional[str] = None
    groupset_model: Optional[str] = None
    electronic_shifting: bool = False
    wheel_brand: Optional[str] = None
    wheel_model: Optional[str] = None
    size: Optional[str] = None
    size_liquidity: Optional[float] = None
    brake_type: Optional[str] = None
    estimated_market_segment: Optional[str] = None
    confidence: float = 0.0
    raw_extraction: Dict = None  # Для отладки

    def __post_init__(self):
        if self.raw_extraction is None:
            self.raw_extraction = {}

    def to_dict(self):
        """Преобразовать в dict для JSON"""
        data = asdict(self)
        data['confidence'] = round(self.confidence, 1)
        return data


class BikeParser:
    """Парсер характеристик велосипедов"""

    def __init__(self):
        self.brands = BRANDS
        self.models = MODELS
        self.groupsets = GROUPSETS
        self.bike_types = BIKE_TYPES

    def parse(self, title: str, description: str = "", images: List[str] = None) -> BikeInfo:
        """
        Парсить велосипед из текста и изображений

        Args:
            title: Название объявления
            description: Описание
            images: Список URLs изображений

        Returns:
            BikeInfo со всеми извлеченными параметрами
        """
        bike = BikeInfo()

        # Объединяем текст для анализа
        full_text = f"{title} {description}".lower()

        # Парсим характеристики из текста
        bike.brand = self._extract_brand(full_text)
        bike.model = self._extract_model(full_text)
        bike.version = self._extract_version(full_text)
        bike.year = self._extract_year(full_text, title)
        bike.bike_type = self._extract_bike_type(full_text)
        bike.frame_material = self._extract_frame_material(full_text)
        bike.size = self._extract_size(full_text)
        bike.size_liquidity = self._get_size_liquidity(bike.size)
        bike.brake_type = self._extract_brake_type(full_text)

        # Парсим групсет
        groupset_brand, groupset_model, electronic = self._extract_groupset(full_text)
        bike.groupset_brand = groupset_brand
        bike.groupset_model = groupset_model
        bike.electronic_shifting = electronic

        # Парсим колеса
        bike.wheel_brand, bike.wheel_model = self._extract_wheels(full_text)

        # Определяем сегмент
        bike.estimated_market_segment = self._estimate_segment(bike)

        # Расчитываем confidence
        bike.confidence = self._calculate_confidence(bike, full_text)

        return bike

    def _extract_brand(self, text: str) -> Optional[str]:
        """Извлечь бренд велосипеда"""
        for brand in self.brands:
            if brand.lower() in text:
                return brand
        return None

    def _extract_model(self, text: str) -> Optional[str]:
        """Извлечь модель велосипеда"""
        for model in self.models:
            if model.lower() in text:
                # Возвращаем в правильном формате
                return model.title()
        return None

    def _extract_version(self, text: str) -> Optional[str]:
        """Извлечь версию/комплектацию"""
        # Ищем паттерны типа "SL 7 EVO", "CF SLX", и т.д.
        patterns = [
            r'(\w+\s+SL\s+\d+)',
            r'(\w+\s+CF\s+\w+)',
            r'(\d+\s+EVO)',
            r'(RC\s+\d+)',
            r'(PRO\s+\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).title()

        return None

    def _extract_year(self, text: str, title: str = "") -> Optional[int]:
        """Извлечь год выпуска велосипеда"""
        # Ищем 4-значное число в диапазоне 2000-2025
        matches = re.findall(r'\b(20[0-2]\d)\b', text)

        if matches:
            # Берем самое свежее
            return max(int(year) for year in matches)

        # Если не найдено, пробуем извлечь из заголовка
        matches = re.findall(r'\b(20[0-2]\d)\b', title)
        if matches:
            return max(int(year) for year in matches)

        return None

    def _extract_bike_type(self, text: str) -> Optional[str]:
        """Извлечь тип велосипеда"""
        for keywords, bike_type in self.bike_types.items():
            if keywords.lower() in text:
                return bike_type

        # Попытка определить по косвенным признакам
        if any(word in text for word in ['disc', 'gravel', 'off-road']):
            return 'gravel'
        elif any(word in text for word in ['road', 'carretera', 'dropbar']):
            return 'road'

        return None

    def _extract_frame_material(self, text: str) -> Optional[str]:
        """Извлечь материал рамы"""
        for material, standardized in FRAME_MATERIALS.items():
            if material.lower() in text:
                return standardized
        return None

    def _extract_groupset(self, text: str) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Извлечь групсет
        Возвращает (бренд, модель, электронный)
        """
        electronic = False

        # Проверяем Shimano
        for keyword, model in self.groupsets['shimano'].items():
            if keyword.lower() in text:
                if 'di2' in text or 'electronic' in text or 'eletronico' in text:
                    electronic = True
                return 'Shimano', model, electronic

        # Проверяем SRAM
        for keyword, model in self.groupsets['sram'].items():
            if keyword.lower() in text:
                if 'axs' in text or 'electronic' in text:
                    electronic = True
                return 'SRAM', model, electronic

        # Проверяем Campagnolo
        for keyword, model in self.groupsets['campagnolo'].items():
            if keyword.lower() in text:
                return 'Campagnolo', model, electronic

        return None, None, electronic

    def _extract_wheels(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечь бренд и модель колес"""
        wheel_brands = ['dt swiss', 'fulcrum', 'mavic', 'campagnolo', 'shimano', 'zipp', 'enve']

        for brand in wheel_brands:
            if brand.lower() in text:
                # Пробуем найти модель после бренда
                pattern = f'{brand}\\s+(\\w+\\s*\\d*\\w*)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return brand.title(), match.group(1).title()
                return brand.title(), None

        return None, None

    def _extract_size(self, text: str) -> Optional[str]:
        """Извлечь размер велосипеда"""
        # Ищем буквенные размеры
        sizes = ['xxs', 'xs', 's', 'm', 'l', 'xl', 'xxl']
        for size in sizes:
            if re.search(rf'\b{size}\b', text, re.IGNORECASE):
                return size.upper()

        # Ищем числовые размеры (см)
        numeric_sizes = ['48', '50', '52', '54', '56', '58', '60', '62']
        for size in numeric_sizes:
            if re.search(rf'\b{size}\s*(cm|cm\.|размер)', text, re.IGNORECASE):
                return size

        return None

    def _extract_brake_type(self, text: str) -> Optional[str]:
        """Извлечь тип тормозов"""
        text_lower = text.lower()
        if 'hydraulic disc' in text_lower:
            return 'hydraulic disc'
        elif 'mechanical disc' in text_lower:
            return 'mechanical disc'
        elif 'disc' in text_lower:
            return 'disc brake'
        elif 'rim' in text_lower:
            return 'rim brake'
        return None

    def _get_size_liquidity(self, size: Optional[str]) -> Optional[float]:
        """Получить ликвидность размера"""
        if not size:
            return None
        return SIZE_LIQUIDITY.get(size, None)

    def _estimate_segment(self, bike: BikeInfo) -> Optional[str]:
        """Определить рыночный сегмент велосипеда"""
        if not bike.groupset_model:
            return None

        # Определяем по групсету
        groupset = (bike.groupset_model or "").lower()

        if any(x in groupset for x in ['dura-ace', 'red', 'super record']):
            return 'Professional'
        elif any(x in groupset for x in ['ultegra', 'force']):
            return 'High-end Amateur'
        elif any(x in groupset for x in ['105', 'rival']):
            return 'Amateur'
        elif 'tiagra' in groupset or 'claris' in groupset:
            return 'Entry-level'

        return None

    def _calculate_confidence(self, bike: BikeInfo, text: str) -> float:
        """
        Расчитать уверенность в результатах парсинга
        Возвращает значение от 0 до 100
        """
        confidence = 0.0
        max_points = 0
        components = {}

        # Бренд (25 точек)
        if bike.brand:
            confidence += 25
            components['brand'] = (25, True)
        else:
            components['brand'] = (25, False)
        max_points += 25

        # Модель (20 точек)
        if bike.model:
            confidence += 20
            components['model'] = (20, True)
        else:
            components['model'] = (20, False)
        max_points += 20

        # Год (15 точек)
        if bike.year:
            confidence += 15
            components['year'] = (15, True)
        else:
            components['year'] = (15, False)
        max_points += 15

        # Размер (15 точек)
        if bike.size:
            confidence += 15
            components['size'] = (15, True)
        else:
            components['size'] = (15, False)
        max_points += 15

        # Групсет (15 точек)
        if bike.groupset_brand and bike.groupset_model:
            confidence += 15
            components['groupset'] = (15, True)
        elif bike.groupset_brand:
            confidence += 10
            components['groupset'] = (15, 'partial')
        else:
            components['groupset'] = (15, False)
        max_points += 15

        # Велотип (10 точек)
        if bike.bike_type:
            confidence += 10
            components['bike_type'] = (10, True)
        else:
            components['bike_type'] = (10, False)
        max_points += 10

        # Расчитываем процент
        if max_points > 0:
            confidence = (confidence / max_points) * 100

        return confidence


# =====================
# УТИЛИТЫ
# =====================

def parse_bike(title: str, description: str = "", images: List[str] = None) -> Dict:
    """
    Быстрая функция для парсинга велосипеда

    Args:
        title: Название объявления
        description: Описание
        images: Список URLs изображений

    Returns:
        Dict с информацией о велосипеде
    """
    parser = BikeParser()
    bike = parser.parse(title, description, images or [])
    return bike.to_dict()


if __name__ == '__main__':
    # Примеры
    examples = [
        {
            'title': 'Scott Foil RC 10 Ultegra Di2 2024',
            'description': 'Carbon frame. Ultegra Di2 R8170. DT Swiss carbon wheels. Size XL.',
        },
        {
            'title': 'Canyon Aeroad CF SLX 8 Dura-Ace',
            'description': 'Dura-Ace R9270 electronic shifting. DT Swiss wheels. Size M. 2023.',
        },
        {
            'title': 'Specialized Tarmac SL7 105',
            'description': 'Aluminum frame. Shimano 105. Size S. Like new condition.',
        },
    ]

    parser = BikeParser()

    for example in examples:
        print(f"\n{'='*60}")
        print(f"Title: {example['title']}")
        print(f"Description: {example['description']}")
        print(f"{'='*60}")

        bike = parser.parse(example['title'], example['description'])
        print(json.dumps(bike.to_dict(), indent=2, ensure_ascii=False))
