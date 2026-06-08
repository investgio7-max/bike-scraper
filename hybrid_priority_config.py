#!/usr/bin/env python3
"""
HYBRID PRIORITY MODE CONFIGURATION
Two-tier system: prioritize high-profit models without losing rare deals
"""

from typing import Dict, Tuple

# ====================================================================
# TIER 1: HIGH PRIORITY (Lower thresholds for premium models)
# ====================================================================

TIER_1_MODELS = {
    'aeroad',       # Canyon - most common, highest profit
    'ultimate',     # Canyon - climbing, high profit
    'tarmac',       # Specialized - very profitable
    'addict rc',    # Scott - excellent deals
    'dogma',        # Pinarello - premium, high profit
    'madone',       # Trek - road, consistent profit
    'emonda',       # Trek - climbing, good profit
    's5',           # Cervelo - premium road
    'tcr',          # Giant - common, good profit
    'roadmachine',  # BMC - premium road
}

# Tier 1 thresholds (more lenient)
TIER_1_MIN_CONFIDENCE = 90      # % - AI confidence
TIER_1_MIN_COMPARABLES = 20     # listings for market comparison
TIER_1_MIN_DISCOUNT = 15        # % - profit margin

# ====================================================================
# TIER 2: NORMAL PRIORITY (Standard thresholds for all other models)
# ====================================================================

# All other models not in TIER_1_MODELS are considered TIER_2
TIER_2_MIN_CONFIDENCE = 90      # % - AI confidence
TIER_2_MIN_COMPARABLES = 25     # listings for market comparison
TIER_2_MIN_DISCOUNT = 25        # % - profit margin

# ====================================================================
# CONFIGURATION
# ====================================================================

HYBRID_MODE_ENABLED = True

# ====================================================================
# FUNCTIONS
# ====================================================================

def get_model_tier(model_name: str) -> str:
    """
    Determine which tier a model belongs to.

    Args:
        model_name: Model name (lowercase)

    Returns:
        "tier_1" or "tier_2"
    """
    if not model_name:
        return "tier_2"

    model_lower = model_name.lower().strip()

    if model_lower in TIER_1_MODELS:
        return "tier_1"
    else:
        return "tier_2"


def get_tier_thresholds(tier: str) -> Dict[str, float]:
    """
    Get filtering thresholds for a specific tier.

    Args:
        tier: "tier_1" or "tier_2"

    Returns:
        Dict with min_confidence, min_comparables, min_discount
    """
    if tier == "tier_1":
        return {
            "min_confidence": TIER_1_MIN_CONFIDENCE,
            "min_comparables": TIER_1_MIN_COMPARABLES,
            "min_discount": TIER_1_MIN_DISCOUNT,
        }
    else:
        return {
            "min_confidence": TIER_2_MIN_CONFIDENCE,
            "min_comparables": TIER_2_MIN_COMPARABLES,
            "min_discount": TIER_2_MIN_DISCOUNT,
        }


def should_send_alert(
    model: str,
    confidence: float,
    comparables: int,
    discount: float
) -> Tuple[bool, str]:
    """
    Determine if alert should be sent based on hybrid priority rules.

    Args:
        model: Model name
        confidence: AI confidence score (0-100)
        comparables: Number of comparable listings
        discount: Discount percentage (0-100)

    Returns:
        (should_send: bool, reason: str, tier: str)
    """

    tier = get_model_tier(model)
    thresholds = get_tier_thresholds(tier)

    # Check confidence threshold
    if confidence < thresholds["min_confidence"]:
        return (
            False,
            f"LOW_CONFIDENCE ({confidence:.0f}% < {thresholds['min_confidence']}%)",
            tier
        )

    # Check comparables threshold
    if comparables < thresholds["min_comparables"]:
        return (
            False,
            f"LOW_COMPARABLES ({comparables} < {thresholds['min_comparables']})",
            tier
        )

    # Check discount threshold
    if discount < thresholds["min_discount"]:
        return (
            False,
            f"LOW_DISCOUNT ({discount:.1f}% < {thresholds['min_discount']}%)",
            tier
        )

    # All thresholds passed
    return (True, f"PASS_{tier.upper()}", tier)


# ====================================================================
# TIER STATISTICS
# ====================================================================

def get_statistics():
    """Get statistics about the configuration"""
    return {
        "hybrid_mode_enabled": HYBRID_MODE_ENABLED,
        "tier_1_models_count": len(TIER_1_MODELS),
        "tier_1_models": sorted(TIER_1_MODELS),
        "tier_1_thresholds": {
            "min_confidence": TIER_1_MIN_CONFIDENCE,
            "min_comparables": TIER_1_MIN_COMPARABLES,
            "min_discount": TIER_1_MIN_DISCOUNT,
        },
        "tier_2_thresholds": {
            "min_confidence": TIER_2_MIN_CONFIDENCE,
            "min_comparables": TIER_2_MIN_COMPARABLES,
            "min_discount": TIER_2_MIN_DISCOUNT,
        },
    }


# ====================================================================
# TESTING
# ====================================================================

if __name__ == "__main__":
    import json

    print("\n" + "="*70)
    print("HYBRID PRIORITY MODE CONFIGURATION")
    print("="*70 + "\n")

    stats = get_statistics()

    print(f"Mode Enabled: {stats['hybrid_mode_enabled']}")
    print(f"Tier 1 Models: {stats['tier_1_models_count']}")
    print(f"\nTier 1 Models: {', '.join(sorted(stats['tier_1_models']))}")

    print(f"\nTier 1 Thresholds:")
    print(f"  Confidence: >= {stats['tier_1_thresholds']['min_confidence']}%")
    print(f"  Comparables: >= {stats['tier_1_thresholds']['min_comparables']}")
    print(f"  Discount: >= {stats['tier_1_thresholds']['min_discount']}%")

    print(f"\nTier 2 Thresholds:")
    print(f"  Confidence: >= {stats['tier_2_thresholds']['min_confidence']}%")
    print(f"  Comparables: >= {stats['tier_2_thresholds']['min_comparables']}")
    print(f"  Discount: >= {stats['tier_2_thresholds']['min_discount']}%")

    # Test examples
    print("\n" + "="*70)
    print("TEST EXAMPLES")
    print("="*70 + "\n")

    test_cases = [
        ("aeroad", 92, 22, 17),      # TIER 1: Should PASS
        ("merida reacto", 92, 22, 17),  # TIER 2: Should FAIL (low discount)
        ("merida reacto", 92, 30, 28),  # TIER 2: Should PASS
        ("tarmac", 88, 30, 25),      # TIER 1: Should FAIL (low confidence)
        ("ultimate", 95, 25, 20),    # TIER 1: Should PASS
    ]

    for model, confidence, comparables, discount in test_cases:
        should_send, reason, tier = should_send_alert(model, confidence, comparables, discount)
        status = "✅ SEND" if should_send else "❌ REJECT"
        print(f"{status} | {model.upper():20} | {confidence}% conf, {comparables} comp, {discount}% disc | {tier.upper():6} | {reason}")

    print("\n" + "="*70 + "\n")
