#!/usr/bin/env python3
"""
Тест Wallapop скрейпера с CloakBrowser
"""

import sys
import asyncio
sys.path.insert(0, '/Users/oleg/bike-scraper')

from bike_scraper.scraper_wallapop import WallapopScraper

async def test_cloak_scraper():
    """Тестировать скрейпер с CloakBrowser"""
    print("\n" + "="*70)
    print("🕷️ TEST: Wallapop Scraper с CloakBrowser")
    print("="*70)

    scraper = WallapopScraper(use_cloak=True)

    try:
        # Ищем велосипеды
        print("\n🔍 Поиск: Canyon Aeroad CF SLX")
        listings = await scraper.search_async(
            search_term="Canyon Aeroad CF SLX",
            max_results=10
        )

        if listings:
            print(f"\n✅ УСПЕХ! Найдено {len(listings)} объявлений\n")

            for i, listing in enumerate(listings[:5], 1):
                print(f"{i}. {listing.title}")
                print(f"   Цена: €{listing.price}")
                print(f"   Продавец: {listing.seller_name}")
                print(f"   Локация: {listing.location}")
                print(f"   URL: {listing.url}")
                print()
        else:
            print("\n⚠️ Объявления не найдены на Wallapop")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Закрыть браузер
        await scraper.close()
        print("\n✅ Тест завершен")

if __name__ == '__main__':
    asyncio.run(test_cloak_scraper())
