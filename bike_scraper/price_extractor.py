"""
Price Extraction & Validation Module for Wallapop

Reliable price extraction with 7-stage validation pipeline:
1. DOM Extraction (from listing card block only)
2. OCR Validation (future: screenshot + OCR)
3. Sanity Check (€300 - €25000 range)
4. UI Noise Filter (ignore ratings, frame sizes, etc)
5. Model Price Validation (using bike model name)
6. Double Confirmation (require 2+ sources to match)
7. Confidence Score (99% = validated, low = rejected)
"""

import re
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class PriceStatus(Enum):
    """Price validation status"""
    VALID = "VALID"
    PRICE_PARSE_ERROR = "PRICE_PARSE_ERROR"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    SUSPICIOUS = "SUSPICIOUS"
    UNCONFIRMED = "UNCONFIRMED"


@dataclass
class PriceResult:
    """Price extraction result with confidence score"""
    price: Optional[float]
    currency: str
    source: str  # "DOM", "DOM + OCR", "DOM + API", etc
    confidence: int  # 0-100
    status: PriceStatus
    validation_details: Dict = None

    def __post_init__(self):
        if self.validation_details is None:
            self.validation_details = {}


class PriceConfig:
    """Configuration for price extraction and validation"""

    # Bike price ranges (in EUR)
    MIN_PRICE = 300  # Cheapest secondhand bike
    MAX_PRICE = 25000  # High-end road bike

    # Premium models (Aeroad, Ultimate, etc) - HIGH-END RANGE
    # Canyon Aeroad actual prices: €25k-€110k (2nd hand cheaper)
    # Other premium models: Trek Madone, Specialized Tarmac, etc: €15k-€50k
    PREMIUM_MODELS = [
        'aeroad', 'ultimate', 'foil', 'tarmac', 'madone',
        'dogma', 'teammachine', 's5', 'r5', 'topstone',
        'speedmax', 'grail'
    ]

    # Premium models are EXPENSIVE secondhand bikes
    PREMIUM_MIN_PRICE = 5000  # Damaged/old premium bikes
    PREMIUM_MAX_PRICE = 120000  # High-end premium (Canyon Aeroad new is €100k+)

    # UI Elements to IGNORE (not prices)
    UI_NOISE_PATTERNS = [
        r'^\d+/\d+$',  # 1/10, 2/10, ratings
        r'^\d+\(\d+\)$',  # 5(3) - some weird format
        r'^\d+\s*cm$',  # 50cm - frame size
        r'^\d+/\d+$',  # 50/34 - gear ratios
        r'^(20\d{2}|202[0-9])$',  # Years: 2024, 2025, 2026
        r'^[a-z]\d+$',  # S5, R5, M10 - size codes
        r'^\d+\.\d+\.\d+$',  # Version numbers
    ]

    # Suspicious keywords that indicate NOT A PRICE
    NOISE_KEYWORDS = [
        'fotos', 'photo', 'imagen', 'image',  # Photo counter
        'comentarios', 'reviews', 'opiniones',  # Reviews count
        'valoraciones',  # Ratings
        'vendedor', 'seller',  # Seller info
        'año', 'year',  # Year
        'tamaño', 'size', 'talla',  # Size
        'velocidades', 'gears',  # Number of gears
        'peso', 'weight',  # Weight
    ]


class PriceExtractor:
    """STAGE 1: DOM Extraction - Extract price from listing card block ONLY"""

    @staticmethod
    def extract_from_element_text(element_text: str) -> Optional[float]:
        """
        Extract price from element text.
        Format: "1 / 3350 €Some Title" -> 3350

        Args:
            element_text: Full text from listing element

        Returns:
            Extracted price or None
        """
        if not element_text or '€' not in element_text:
            return None

        # Split on € to separate price part from title
        parts = element_text.split('€', 1)
        if len(parts) < 2:
            return None

        price_part = parts[0].strip()

        # Extract last number before € (ignores "1 / " prefix)
        # Pattern: "1 / 3350 " -> matches "3350"
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*$', price_part)
        if not match:
            logger.debug(f"No price found in price_part: {price_part}")
            return None

        price_text = match.group(1)
        return PriceExtractor._normalize_price(price_text)

    @staticmethod
    def _normalize_price(price_text: str) -> float:
        """Convert price text to float"""
        if not price_text:
            return None

        # Remove spaces and convert comma to dot
        price_text = price_text.replace(' ', '').replace(',', '.')

        try:
            return float(price_text)
        except ValueError:
            logger.debug(f"Failed to convert price text to float: {price_text}")
            return None


class PriceValidator:
    """Multi-stage price validation pipeline"""

    @staticmethod
    def validate(
        price: Optional[float],
        title: str = "",
        source: str = "DOM"
    ) -> PriceResult:
        """
        Validate price through multi-stage pipeline

        Args:
            price: Extracted price value
            title: Bike model/title (for model validation)
            source: Source of price extraction (DOM, OCR, API)

        Returns:
            PriceResult with validation status and confidence score
        """

        # Stage 1: Check if price exists
        if price is None:
            return PriceResult(
                price=None,
                currency="EUR",
                source=source,
                confidence=0,
                status=PriceStatus.PRICE_PARSE_ERROR,
                validation_details={"reason": "No price extracted"}
            )

        # Stage 2: UI Noise Filter - ignore non-price numbers
        if PriceValidator._is_ui_noise(price, title):
            return PriceResult(
                price=None,
                currency="EUR",
                source=source,
                confidence=0,
                status=PriceStatus.PRICE_PARSE_ERROR,
                validation_details={"reason": "Detected as UI noise (rating, size, year, etc)"}
            )

        # Stage 3: Sanity Check - basic range validation
        is_premium = PriceValidator._is_premium_model(title)
        min_price = PriceConfig.PREMIUM_MIN_PRICE if is_premium else PriceConfig.MIN_PRICE
        max_price = PriceConfig.PREMIUM_MAX_PRICE if is_premium else PriceConfig.MAX_PRICE

        if price < min_price or price > max_price:
            return PriceResult(
                price=price,
                currency="EUR",
                source=source,
                confidence=15,
                status=PriceStatus.OUT_OF_RANGE,
                validation_details={
                    "reason": f"Out of range: €{min_price}-€{max_price}",
                    "is_premium": is_premium
                }
            )

        # Stage 4: Model Price Validation
        if is_premium and not (PriceConfig.PREMIUM_MIN_PRICE <= price <= PriceConfig.PREMIUM_MAX_PRICE):
            return PriceResult(
                price=price,
                currency="EUR",
                source=source,
                confidence=40,
                status=PriceStatus.SUSPICIOUS,
                validation_details={
                    "reason": f"Premium model but price suspicious: €{price}",
                    "expected_range": f"€{PriceConfig.PREMIUM_MIN_PRICE}-€{PriceConfig.PREMIUM_MAX_PRICE}"
                }
            )

        # If we got here, price passed all checks
        confidence = 95 if source in ["DOM + OCR", "DOM + API"] else 85

        return PriceResult(
            price=price,
            currency="EUR",
            source=source,
            confidence=confidence,
            status=PriceStatus.VALID,
            validation_details={"passed_all_checks": True}
        )

    @staticmethod
    def _is_ui_noise(price: float, title: str = "") -> bool:
        """
        Check if number looks like UI noise (rating, size, year, etc)
        NOT a price
        """
        price_str = str(int(price))

        # Check UI noise patterns
        for pattern in PriceConfig.UI_NOISE_PATTERNS:
            if re.match(pattern, price_str):
                logger.debug(f"Price {price} matches UI noise pattern: {pattern}")
                return True

        # Single/double digit numbers are suspicious (except in title context)
        if price < 100:
            # Could be frame size (50cm), gear count (21), etc
            logger.debug(f"Price {price} is very low, might be UI element")
            return True

        return False

    @staticmethod
    def _is_premium_model(title: str) -> bool:
        """Check if bike is premium model"""
        if not title:
            return False

        title_lower = title.lower()
        for model in PriceConfig.PREMIUM_MODELS:
            if model in title_lower:
                return True

        return False


class PriceConfirmation:
    """STAGE 6: Double Confirmation - require 2+ sources to match"""

    @staticmethod
    def confirm_price(
        dom_price: Optional[float],
        ocr_price: Optional[float] = None,
        api_price: Optional[float] = None,
        tolerance_percent: float = 5.0  # 5% tolerance
    ) -> PriceResult:
        """
        Confirm price by comparing multiple sources.

        Requires at least 2 sources to match (within tolerance)

        Args:
            dom_price: Price from DOM extraction
            ocr_price: Price from OCR (optional)
            api_price: Price from API (optional)
            tolerance_percent: Tolerance for matching (%)

        Returns:
            PriceResult with confirmation status
        """

        sources = {
            "DOM": dom_price,
            "OCR": ocr_price,
            "API": api_price,
        }
        sources = {k: v for k, v in sources.items() if v is not None}

        if not sources:
            return PriceResult(
                price=None,
                currency="EUR",
                source="NONE",
                confidence=0,
                status=PriceStatus.PRICE_PARSE_ERROR,
                validation_details={"reason": "No sources available"}
            )

        # If only one source, return with low confidence
        if len(sources) == 1:
            source_name = list(sources.keys())[0]
            price = sources[source_name]
            return PriceResult(
                price=price,
                currency="EUR",
                source=source_name,
                confidence=70,
                status=PriceStatus.UNCONFIRMED,
                validation_details={"reason": "Only one source available"}
            )

        # Check if prices match (within tolerance)
        prices = list(sources.values())
        main_price = prices[0]

        all_match = all(
            abs(p - main_price) / main_price * 100 <= tolerance_percent
            for p in prices
        )

        if all_match:
            matching_sources = " + ".join(sources.keys())
            return PriceResult(
                price=main_price,
                currency="EUR",
                source=matching_sources,
                confidence=99,
                status=PriceStatus.VALID,
                validation_details={"reason": "All sources match", "tolerance_percent": tolerance_percent}
            )
        else:
            # Sources disagree
            return PriceResult(
                price=None,
                currency="EUR",
                source="MISMATCH",
                confidence=0,
                status=PriceStatus.PRICE_PARSE_ERROR,
                validation_details={
                    "reason": "Multiple sources disagree",
                    "sources": sources
                }
            )
