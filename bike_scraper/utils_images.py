"""
Скачивание и управление изображениями
"""

import os
import hashlib
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from curl_cffi.requests import Session

from config import IMAGES_DIR, MAX_IMAGE_SIZE_MB, DOWNLOAD_IMAGES
from utils_logger import get_logger

logger = get_logger(__name__)


class ImageDownloader:
    """Скачивание изображений от объявлений"""

    def __init__(self):
        self.images_dir = Path(IMAGES_DIR)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.session = Session()
        self.max_size = MAX_IMAGE_SIZE_MB * 1024 * 1024

    def download_images(self, listing_id: str, image_urls: List[str]) -> dict:
        """
        Скачать все изображения для объявления
        Возвращает: {'main_image': path, 'images': [paths]}
        """
        if not DOWNLOAD_IMAGES or not image_urls:
            return {'main_image': None, 'images': []}

        logger.info(f"📸 Скачиваю {len(image_urls)} изображений для {listing_id}")

        downloaded_paths = []
        errors = []

        # Скачиваем изображения параллельно
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._download_single, listing_id, url, idx): url
                for idx, url in enumerate(image_urls)
            }

            for future in as_completed(futures):
                url = futures[future]
                try:
                    result = future.result()
                    if result:
                        downloaded_paths.append(result)
                except Exception as e:
                    logger.warning(f"❌ Ошибка скачивания {url}: {e}")
                    errors.append({'url': url, 'error': str(e)})

        if downloaded_paths:
            logger.info(f"✅ Скачано {len(downloaded_paths)} из {len(image_urls)} изображений")

        return {
            'main_image': downloaded_paths[0] if downloaded_paths else None,
            'images': downloaded_paths,
            'errors': errors
        }

    def _download_single(self, listing_id: str, url: str, index: int) -> Optional[str]:
        """Скачать одно изображение"""
        try:
            # Пропускаем если нет URL
            if not url or 'http' not in url:
                return None

            # Создаем имя файла
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            ext = '.jpg'  # По умолчанию JPG

            # Проверяем расширение из URL
            if '.' in url.split('/')[-1]:
                ext = '.' + url.split('.')[-1].split('?')[0]

            filename = f"{listing_id}_{index}_{url_hash}{ext}"
            filepath = self.images_dir / filename

            # Если уже скачано, пропускаем
            if filepath.exists():
                return str(filepath)

            # Скачиваем с таймаутом
            response = self.session.get(
                url,
                timeout=10,
                impersonate='chrome120',
                stream=True
            )
            response.raise_for_status()

            # Проверяем размер
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > self.max_size:
                logger.warning(f"⚠️  Изображение {filename} слишком большое ({content_length} bytes)")
                return None

            # Сохраняем
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"✓ Скачано {filename}")
            return str(filepath)

        except Exception as e:
            logger.debug(f"❌ Ошибка скачивания {url}: {e}")
            return None

    def cleanup_unused_images(self, active_listing_ids: set) -> int:
        """
        Удалить изображения для неактивных объявлений
        Возвращает количество удаленных файлов
        """
        deleted_count = 0

        for image_file in self.images_dir.glob('*'):
            # Парсим listing_id из имени файла
            listing_id = image_file.name.split('_')[0]

            if listing_id not in active_listing_ids:
                try:
                    image_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"⚠️  Не удалось удалить {image_file}: {e}")

        if deleted_count > 0:
            logger.info(f"🗑️  Удалено {deleted_count} неиспользуемых изображений")

        return deleted_count

    def get_image_stats(self) -> dict:
        """Получить статистику изображений"""
        total_size = 0
        total_files = 0

        for image_file in self.images_dir.glob('*'):
            total_size += image_file.stat().st_size
            total_files += 1

        return {
            'total_files': total_files,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'directory': str(self.images_dir)
        }
