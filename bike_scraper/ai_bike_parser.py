"""
🤖 AI Bike Parser - Полнофункциональный парсер велосипедов

Объединяет:
- Regex парсинг текста
- OCR анализ изображений
- Claude Vision API анализ
- Расчет confidence score
- Обработка тысяч объявлений
"""

import json
import logging
from typing import Optional, List, Dict
from dataclasses import asdict

from bike_scraper.ai_parser import BikeParser, BikeInfo, parse_bike
from bike_scraper.image_analyzer import ImageAnalyzer, LocalOCR

logger = logging.getLogger(__name__)


class AIBikeParser:
    """Полнофункциональный AI парсер велосипедов"""

    def __init__(self, api_key: Optional[str] = None, use_vision: bool = True):
        """
        Инициализировать парсер

        Args:
            api_key: Anthropic API ключ (опционально, для Claude Vision)
            use_vision: Использовать ли Claude Vision для анализа изображений
        """
        self.text_parser = BikeParser()
        self.image_analyzer = ImageAnalyzer(api_key) if use_vision else None
        self.local_ocr = LocalOCR()

    def parse(
        self,
        title: str,
        description: str = "",
        images: List[str] = None,
        analyze_images: bool = True
    ) -> BikeInfo:
        """
        Полный парсинг велосипеда с использованием текста и изображений

        Args:
            title: Название объявления
            description: Описание
            images: Список URLs изображений
            analyze_images: Анализировать ли изображения

        Returns:
            BikeInfo со всеми извлеченными параметрами
        """
        # Начинаем с текстового парсинга
        bike = self.text_parser.parse(title, description, images or [])

        # Если есть изображения и нужно их анализировать
        if analyze_images and images and self.image_analyzer:
            logger.info(f"📸 Анализирую {len(images)} изображение(й)")

            # Сначала пробуем OCR
            ocr_text = ""
            for image_url in images[:3]:  # Первые 3 изображения
                try:
                    ocr_text += self.image_analyzer.extract_text_from_image(image_url) + "\n"
                except Exception as e:
                    logger.debug(f"OCR ошибка: {e}")

            # Если OCR дал результаты, переанализируем с новым текстом
            if ocr_text:
                combined_text = f"{title} {description} {ocr_text}".lower()
                bike.brand = bike.brand or self.text_parser._extract_brand(combined_text)
                bike.model = bike.model or self.text_parser._extract_model(combined_text)
                bike.year = bike.year or self.text_parser._extract_year(combined_text)

            # Анализируем изображения для дополнительной информации
            for image_url in images[:2]:  # Первые 2 изображения
                try:
                    image_analysis = self.image_analyzer.analyze_bike_image(image_url)

                    # Заполняем недостающую информацию из анализа изображения
                    if not bike.year and 'year' in image_analysis:
                        bike.year = image_analysis.get('year')
                    if not bike.frame_material and 'frame_material' in image_analysis:
                        bike.frame_material = image_analysis.get('frame_material')
                    if not bike.bike_type and 'bike_type' in image_analysis:
                        bike.bike_type = image_analysis.get('bike_type')
                    if not bike.brake_type and 'brake_type' in image_analysis:
                        bike.brake_type = image_analysis.get('brake_type')

                except Exception as e:
                    logger.debug(f"Ошибка анализа изображения: {e}")

            # Если год все еще не найден, пробуем оценить из изображения
            if not bike.year and images:
                try:
                    estimated_year = self.image_analyzer.estimate_year_from_image(images[0])
                    if estimated_year:
                        bike.year = estimated_year
                except Exception as e:
                    logger.debug(f"Ошибка оценки года: {e}")

        # Пересчитываем confidence с новой информацией
        full_text = f"{title} {description}"
        bike.confidence = self.text_parser._calculate_confidence(bike, full_text)

        return bike

    def parse_batch(
        self,
        listings: List[Dict[str, any]],
        analyze_images: bool = True,
        batch_size: int = 10
    ) -> List[BikeInfo]:
        """
        Парсить батч объявлений

        Args:
            listings: Список объявлений с title, description, images
            analyze_images: Анализировать ли изображения
            batch_size: Размер батча для логирования

        Returns:
            Список BikeInfo
        """
        results = []

        for i, listing in enumerate(listings):
            try:
                bike = self.parse(
                    title=listing.get('title', ''),
                    description=listing.get('description', ''),
                    images=listing.get('images', []),
                    analyze_images=analyze_images
                )
                results.append(bike)

                if (i + 1) % batch_size == 0:
                    logger.info(f"✅ Обработано {i + 1}/{len(listings)} объявлений")

            except Exception as e:
                logger.error(f"❌ Ошибка парсинга объявления {i}: {e}")
                results.append(None)

        logger.info(f"✅ Завершено: {len([r for r in results if r])} из {len(listings)} объявлений")

        return [r for r in results if r is not None]

    def to_json(self, bike: BikeInfo) -> str:
        """Преобразовать результат в JSON"""
        return json.dumps(bike.to_dict(), indent=2, ensure_ascii=False)


# =====================
# БЫСТРЫЕ ФУНКЦИИ
# =====================

def parse_bike_full(
    title: str,
    description: str = "",
    images: List[str] = None,
    api_key: Optional[str] = None
) -> Dict:
    """
    Быстрая функция для полного парсинга велосипеда

    Args:
        title: Название объявления
        description: Описание
        images: Список URLs изображений
        api_key: Anthropic API ключ (опционально)

    Returns:
        Dict с информацией о велосипеде
    """
    parser = AIBikeParser(api_key=api_key, use_vision=bool(api_key))
    bike = parser.parse(title, description, images or [])
    return bike.to_dict()


if __name__ == '__main__':
    # Примеры использования
    logging.basicConfig(level=logging.INFO)

    # Создаем парсер
    parser = AIBikeParser()

    # Пример 1: Простой парсинг
    print("="*60)
    print("ПРИМЕР 1: Простой парсинг текста")
    print("="*60)

    bike1 = parser.parse(
        title="Scott Foil RC 10 Ultegra Di2 2024",
        description="Carbon frame. Ultegra Di2 R8170. DT Swiss carbon wheels. Size XL."
    )
    print(parser.to_json(bike1))

    # Пример 2: Батч обработка
    print("\n" + "="*60)
    print("ПРИМЕР 2: Батч обработка")
    print("="*60)

    listings = [
        {
            'title': 'Canyon Aeroad CF SLX 8 Dura-Ace',
            'description': 'Dura-Ace R9270. Size M. 2023.',
            'images': []
        },
        {
            'title': 'Specialized Tarmac SL7 105',
            'description': 'Shimano 105. Size S.',
            'images': []
        },
        {
            'title': 'Trek Madone SLR',
            'description': 'Dura-Ace. Carbon. Size 54cm.',
            'images': []
        }
    ]

    results = parser.parse_batch(listings, analyze_images=False)
    print(f"Обработано {len(results)} объявлений")
    for i, result in enumerate(results):
        print(f"\n{i+1}. {result.brand} {result.model} - Confidence: {result.confidence:.0f}%")
