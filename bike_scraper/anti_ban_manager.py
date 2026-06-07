"""
🛡️ Anti-Ban Manager - Стратегии для избежания блокировки Cloudflare

Методы:
1. Ротация User-Agent
2. Случайные задержки
3. Обнаружение блокировки и паузы
4. Распределение запросов по времени
5. Кэширование результатов
"""

import random
import time
from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class AntiBanManager:
    """Менеджер для избежания блокировки Cloudflare"""

    # Ротация User-Agent
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    ]

    def __init__(self, min_delay: float = 1, max_delay: float = 5):
        """
        Инициализировать Anti-Ban менеджер

        Args:
            min_delay: Минимальная задержка между запросами (сек)
            max_delay: Максимальная задержка между запросами (сек)
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = None
        self.ban_detected_at = None
        self.ban_cooldown_duration = 3600  # 1 час пауза при 403
        self.request_count = 0
        self.error_count = 0

    def get_random_user_agent(self) -> str:
        """Получить случайный User-Agent"""
        return random.choice(self.USER_AGENTS)

    def get_random_delay(self) -> float:
        """Получить случайную задержку (не паттерны)"""
        # Добавляем вариативность: базовая задержка + random
        base = random.uniform(self.min_delay, self.max_delay)
        # Иногда добавляем дополнительную паузу (имитируем чтение)
        if random.random() < 0.15:  # 15% шанс дополнительной паузы
            base += random.uniform(2, 5)
        return base

    def wait_before_request(self, force_wait: bool = False) -> None:
        """
        Ждать перед запросом

        Args:
            force_wait: Принудительно ждать (даже если первый запрос)
        """
        # Проверяем если был бан
        if self.is_banned():
            cooldown_time = self.get_ban_cooldown_remaining()
            logger.warning(f"⏸️  IP заблокирован! Пауза {cooldown_time} сек...")
            time.sleep(cooldown_time)
            self.reset_ban()
            return

        # Обычная задержка
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            delay = self.get_random_delay()

            if elapsed < delay:
                wait_time = delay - elapsed
                logger.debug(f"⏳ Жду {wait_time:.1f}s перед следующим запросом...")
                time.sleep(wait_time)

        self.last_request_time = time.time()

    def on_request_success(self) -> None:
        """Зафиксировать успешный запрос"""
        self.request_count += 1
        self.error_count = 0  # Сброс счетчика ошибок

        if self.request_count % 10 == 0:
            logger.info(f"✅ {self.request_count} успешных запросов")

    def on_request_error(self, status_code: Optional[int] = None) -> None:
        """
        Зафиксировать ошибку запроса

        Args:
            status_code: HTTP статус код (если 403 → считаем это блокировкой)
        """
        self.error_count += 1

        if status_code == 403:
            self.detect_ban()
            logger.error("🚨 403 FORBIDDEN! IP ЗАБЛОКИРОВАН!")

        elif self.error_count >= 5:
            logger.warning(f"⚠️ {self.error_count} ошибок подряд - активирую расширенный режим ожидания")
            time.sleep(random.uniform(10, 30))
            self.error_count = 0

    def is_banned(self) -> bool:
        """Проверить если IP еще в бане"""
        if not self.ban_detected_at:
            return False

        elapsed = (datetime.utcnow() - self.ban_detected_at).total_seconds()
        return elapsed < self.ban_cooldown_duration

    def detect_ban(self) -> None:
        """Зафиксировать блокировку"""
        self.ban_detected_at = datetime.utcnow()
        logger.error(f"🔴 БАН ЗАФИКСИРОВАН в {self.ban_detected_at}")

    def get_ban_cooldown_remaining(self) -> float:
        """Получить оставшееся время до разбана"""
        if not self.ban_detected_at:
            return 0

        elapsed = (datetime.utcnow() - self.ban_detected_at).total_seconds()
        remaining = self.ban_cooldown_duration - elapsed

        return max(0, remaining)

    def reset_ban(self) -> None:
        """Сбросить статус блокировки"""
        self.ban_detected_at = None
        logger.info("✅ Статус блокировки сброшен")

    def get_adaptive_delay(self, error_rate: float) -> float:
        """
        Адаптивная задержка на основе частоты ошибок

        Args:
            error_rate: Процент ошибок (0-100)

        Returns:
            Рекомендуемая задержка в секундах
        """
        if error_rate > 50:  # > 50% ошибок
            return random.uniform(30, 60)  # 30-60 сек пауза
        elif error_rate > 20:  # > 20% ошибок
            return random.uniform(15, 30)  # 15-30 сек пауза
        elif error_rate > 10:  # > 10% ошибок
            return random.uniform(5, 15)  # 5-15 сек пауза
        else:
            return self.get_random_delay()  # Обычная задержка

    def should_skip_search(self, search_index: int, total_searches: int) -> bool:
        """
        Пропустить ли этот поиск (для распределения нагрузки)

        Args:
            search_index: Индекс поиска (0-based)
            total_searches: Всего поисков в цикле

        Returns:
            True если нужно пропустить этот поиск в этом цикле
        """
        # Пропускаем ~30% поисков для разгрузки
        if random.random() < 0.3:
            logger.info(f"⏭️  Пропускаю поиск #{search_index + 1} для разгрузки")
            return True

        return False

    def get_safe_max_results(self, base_max: int = 50) -> int:
        """
        Получить безопасное количество результатов за запрос

        Returns:
            Количество результатов (уменьшается при высокой ошибке)
        """
        if self.error_count > 3:
            # При ошибках уменьшаем до 20
            return 20
        elif self.error_count > 1:
            # При 1-3 ошибках уменьшаем до 30
            return 30
        else:
            return base_max


class RateLimiter:
    """Ограничитель частоты запросов"""

    def __init__(self, requests_per_hour: int = 100):
        """
        Args:
            requests_per_hour: Максимум запросов в час
        """
        self.requests_per_hour = requests_per_hour
        self.request_times: List[float] = []

    def is_rate_limited(self) -> bool:
        """Проверить если превышен лимит"""
        now = time.time()
        hour_ago = now - 3600

        # Удаляем старые запросы
        self.request_times = [t for t in self.request_times if t > hour_ago]

        return len(self.request_times) >= self.requests_per_hour

    def add_request(self) -> None:
        """Зафиксировать новый запрос"""
        self.request_times.append(time.time())

    def get_wait_time(self) -> float:
        """Получить время ожидания до следующего запроса"""
        if not self.request_times:
            return 0

        oldest_request = min(self.request_times)
        elapsed = time.time() - oldest_request
        wait_time = 3600 - elapsed

        return max(0, wait_time)
