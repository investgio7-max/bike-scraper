"""
🖼️ Image Analyzer - Анализ изображений велосипедов с помощью AI

Использует:
- Claude Vision API для анализа изображений
- OCR для распознавания текста на фото
- AI-анализ для определения характеристик
"""

import base64
import requests
from typing import Optional, Dict, List
from pathlib import Path
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Анализ изображений велосипедов"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализировать анализатор

        Args:
            api_key: Anthropic API ключ (используется для Claude Vision)
        """
        self.api_key = api_key
        self.client = None

        if api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=api_key)
            except ImportError:
                logger.warning("Anthropic SDK не установлен. OCR функции будут ограничены.")

    def extract_text_from_image(self, image_url: str) -> str:
        """
        Извлечь текст из изображения используя Claude Vision

        Args:
            image_url: URL изображения

        Returns:
            Извлеченный текст
        """
        if not self.client:
            logger.warning("Anthropic SDK не настроен. Пропускаю OCR.")
            return ""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": image_url,
                                },
                            },
                            {
                                "type": "text",
                                "text": "Extract all text visible in this image. Include brand names, model names, specifications, and any other readable text. Return only the extracted text."
                            }
                        ],
                    }
                ],
            )

            return message.content[0].text

        except Exception as e:
            logger.error(f"Ошибка при OCR: {e}")
            return ""

    def analyze_bike_image(self, image_url: str) -> Dict:
        """
        Анализировать изображение велосипеда и извлечь характеристики

        Args:
            image_url: URL изображения

        Returns:
            Dict с извлеченными характеристиками
        """
        if not self.client:
            logger.warning("Anthropic SDK не настроен.")
            return {}

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": image_url,
                                },
                            },
                            {
                                "type": "text",
                                "text": """Analyze this bicycle image and extract the following information:

1. Brand name (if visible)
2. Model name (if visible)
3. Frame material (carbon, aluminum, steel, titanium)
4. Groupset brand and model (Shimano, SRAM, Campagnolo, etc.)
5. Wheel brand and model (if visible)
6. Brake type (rim, disc, hydraulic disc)
7. Bike type (road, gravel, cyclocross, etc.)
8. Color
9. Size (if visible)
10. Year/edition (if visible or estimable from design)
11. Estimated market segment (Professional, High-end Amateur, Amateur, Entry-level)
12. Overall condition (New, Like New, Good, Fair)

Return the response as a JSON object with these fields.
Be specific and extract only what you can clearly see.
For uncertain information, mark as "uncertain" instead of guessing."""
                            }
                        ],
                    }
                ],
            )

            # Парсим JSON из ответа
            response_text = message.content[0].text

            # Пробуем найти JSON в ответе
            try:
                import json
                # Ищем JSON блок в ответе
                start = response_text.find('{')
                end = response_text.rfind('}') + 1

                if start != -1 and end > start:
                    json_str = response_text[start:end]
                    return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                logger.warning("Не удалось распарсить JSON из ответа")

            return {"raw_response": response_text}

        except Exception as e:
            logger.error(f"Ошибка при анализе изображения: {e}")
            return {}

    def estimate_year_from_image(self, image_url: str) -> Optional[int]:
        """
        Оценить год выпуска велосипеда по изображению

        Анализирует:
        - Форму рамы
        - Раскраску
        - Компоненты
        - Колеса
        - Другие видимые элементы

        Args:
            image_url: URL изображения

        Returns:
            Предполагаемый год или None
        """
        if not self.client:
            return None

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "url",
                                    "url": image_url,
                                },
                            },
                            {
                                "type": "text",
                                "text": """Estimate the year/model year of this bicycle based on:
1. Frame design and shape
2. Color scheme and paint style
3. Component styles (shifters, brake design, wheel design)
4. Overall bike design trends

Provide your best estimate as a single year number (2019, 2020, 2021, etc.).
Only respond with the year number, nothing else.
If you cannot estimate, respond with "unknown"."""
                            }
                        ],
                    }
                ],
            )

            response_text = message.content[0].text.strip()

            if response_text == "unknown":
                return None

            try:
                return int(response_text)
            except ValueError:
                return None

        except Exception as e:
            logger.error(f"Ошибка при оценке года: {e}")
            return None

    def analyze_multiple_images(self, image_urls: List[str]) -> Dict:
        """
        Анализировать несколько изображений одного велосипеда

        Args:
            image_urls: Список URLs изображений

        Returns:
            Dict с объединенной информацией
        """
        results = {
            'images_analyzed': 0,
            'extracted_texts': [],
            'analyses': [],
            'confidence': 0.0
        }

        for image_url in image_urls[:5]:  # Анализируем максимум 5 изображений
            try:
                # Извлекаем текст
                text = self.extract_text_from_image(image_url)
                if text:
                    results['extracted_texts'].append(text)

                # Анализируем изображение
                analysis = self.analyze_bike_image(image_url)
                if analysis:
                    results['analyses'].append(analysis)

                results['images_analyzed'] += 1

            except Exception as e:
                logger.warning(f"Ошибка при анализе изображения {image_url}: {e}")

        # Расчитываем confidence на основе количества проанализированных изображений
        if results['images_analyzed'] > 0:
            results['confidence'] = min(100, results['images_analyzed'] * 20)

        return results


class LocalOCR:
    """Локальный OCR используя pytesseract (опционально)"""

    def __init__(self):
        """Инициализировать OCR"""
        try:
            import pytesseract
            from PIL import Image
            self.pytesseract = pytesseract
            self.Image = Image
            self.available = True
        except ImportError:
            logger.warning("pytesseract или PIL не установлены. Локальный OCR недоступен.")
            self.available = False

    def extract_text_from_file(self, image_path: str) -> str:
        """
        Извлечь текст из локального файла изображения

        Args:
            image_path: Путь к изображению

        Returns:
            Извлеченный текст
        """
        if not self.available:
            return ""

        try:
            image = self.Image.open(image_path)
            text = self.pytesseract.image_to_string(image, lang='eng')
            return text
        except Exception as e:
            logger.error(f"Ошибка OCR: {e}")
            return ""

    def extract_text_from_url(self, image_url: str) -> str:
        """
        Извлечь текст из URL изображения

        Args:
            image_url: URL изображения

        Returns:
            Извлеченный текст
        """
        if not self.available:
            return ""

        try:
            response = requests.get(image_url, timeout=10)
            image = self.Image.open(BytesIO(response.content))
            text = self.pytesseract.image_to_string(image, lang='eng')
            return text
        except Exception as e:
            logger.error(f"Ошибка OCR: {e}")
            return ""


if __name__ == '__main__':
    # Пример использования
    analyzer = ImageAnalyzer()

    # Тестовое изображение
    test_image = "https://example.com/bike.jpg"

    print("Анализирую изображение...")
    result = analyzer.analyze_bike_image(test_image)
    print(result)
