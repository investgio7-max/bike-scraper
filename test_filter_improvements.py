#!/usr/bin/env python3
"""
Test Filter Improvements
Verify all 3 false positives from first run are now caught
"""

import logging
from bike_scraper.advanced_filters import AdvancedFilters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_filters")

# Test data from first live run - the 3 failures
test_cases = [
    {
        "name": "Alert #4 - Giant TCR Advanced Pro",
        "title": "Giant TCR Advanced Pro XL 2024",
        "description": "Excellent condition, professional maintained",
        "url": "https://es.wallapop.com/item/8904526",
        "model": {"brand": "Giant", "model": "TCR Advanced Pro"},
        "expected_failure": "URL_404",
        "expected_reject": True,
    },
    {
        "name": "Alert #7 - Argon 18 Gallium Pro (Model Mismatch)",
        "title": "Argon 18 Serenium Pro Carbon Road Bike",
        "description": "High-end racing bike, 10-speed Shimano",
        "url": "https://es.wallapop.com/item/8904529",
        "model": {"brand": "Argon 18", "model": "Gallium Pro"},
        "expected_failure": "MODEL_MISMATCH",
        "expected_reject": True,
    },
    {
        "name": "Alert #10 - Felt FR Advanced (Frame Only)",
        "title": "Felt FR Advanced Carbon Frame Only - M Size",
        "description": "Frame solo, excelente condición, sin daños. Marco de carbono puro",
        "url": "https://es.wallapop.com/item/8904532",
        "model": {"brand": "Felt", "model": "FR Advanced"},
        "expected_failure": "FRAME_ONLY",
        "expected_reject": True,
    },
]

# Test cases that should pass (from the 7 passing alerts)
passing_cases = [
    {
        "name": "Alert #1 - Trek Domane AL 3 (Should Pass)",
        "title": "Trek Domane AL 3 2024 M Size Road Bike Completa",
        "description": "Pristine Trek Domane completa. Shimano Sora groupset, aluminum frame",
        "url": "https://es.wallapop.com/item/8904523",
        "model": {"brand": "Trek", "model": "Domane AL 3"},
        "expected_reject": False,
    },
    {
        "name": "Alert #5 - Scott Speedster (Should Pass)",
        "title": "Scott Speedster 10 Bicicleta Completa",
        "description": "Bicicleta completa lista para rodar. Excellent condition",
        "url": "https://es.wallapop.com/item/8904527",
        "model": {"brand": "Scott", "model": "Speedster 10"},
        "expected_reject": False,
    },
]

def test_filters():
    """Test all filters"""

    logger.info("\n" + "="*80)
    logger.info("🔍 TESTING FILTER IMPROVEMENTS")
    logger.info("="*80)

    logger.info("\n📋 TEST 1: Catch 3 False Positives from Previous Run")
    logger.info("-" * 80)

    caught_count = 0
    for test in test_cases:
        should_send, reason, confidence = AdvancedFilters.apply_all_filters(
            title=test["title"],
            description=test["description"],
            url=test["url"],
            parsed_model=test["model"],
            current_confidence=92
        )

        status = "✅ CAUGHT" if not should_send else "❌ MISSED"
        logger.info(f"\n{status}: {test['name']}")
        logger.info(f"  Expected: REJECT ({test['expected_failure']})")
        logger.info(f"  Actual: {reason}")

        if not should_send:
            caught_count += 1

    logger.info(f"\n📊 Result: {caught_count}/3 false positives caught")

    # Test that good ones still pass
    logger.info("\n\n📋 TEST 2: Good Alerts Still Pass")
    logger.info("-" * 80)

    passed_count = 0
    for test in passing_cases:
        should_send, reason, confidence = AdvancedFilters.apply_all_filters(
            title=test["title"],
            description=test["description"],
            url=test["url"],
            parsed_model=test["model"],
            current_confidence=92
        )

        status = "✅ PASS" if should_send else "❌ FAIL"
        logger.info(f"\n{status}: {test['name']}")
        logger.info(f"  Reason: {reason}")

        if should_send:
            passed_count += 1

    logger.info(f"\n📊 Result: {passed_count}/2 good alerts passed")

    # Final verdict
    logger.info("\n" + "="*80)
    logger.info("🎯 FILTER TEST RESULTS")
    logger.info("="*80)

    all_pass = caught_count == 3 and passed_count == 2

    if all_pass:
        logger.info("\n✅ ALL TESTS PASSED!")
        logger.info(f"   ✅ Caught all 3 false positives")
        logger.info(f"   ✅ Good alerts still pass")
        logger.info(f"\n   Filters are ready for production!")
    else:
        logger.info(f"\n❌ TESTS FAILED")
        logger.info(f"   False positives caught: {caught_count}/3")
        logger.info(f"   Good alerts passed: {passed_count}/2")

    logger.info("="*80 + "\n")

    return all_pass

if __name__ == "__main__":
    success = test_filters()
    exit(0 if success else 1)
