#!/usr/bin/env python3
"""
Advanced Filters Module
Reduces false positives in deal detection
- URL availability check
- Frame/parts only detection
- Complete bike verification
- Model verification
"""

import re
import logging
import asyncio
from typing import Dict, Tuple, Optional
import httpx

logger = logging.getLogger("advanced_filters")

class AdvancedFilters:
    """Advanced filtering to reduce false positives"""

    # Pattern definitions
    FRAME_ONLY_PATTERNS = [
        r"solo\s+cuadro",
        r"solo\s+marco",
        r"frameset",
        r"frame\s+only",
        r"kit\s+cuadro",
        r"cuadro\s+carbono",
        r"marco\s+bicicleta",
        r"fork\s*\+\s*frame",
        r"horquilla\s+cuadro",
    ]

    PARTS_ONLY_PATTERNS = [
        r"ruedas\s+(?!montadas|completa)",
        r"wheelset",
        r"groupset",
        r"grupo\s+(?!completo)",
        r"horquilla\s+(?!bike|bicicleta)",
        r"fork\s+(?!bike|bicicleta)",
        r"manillar",
        r"handlebar",
        r"potencia\s+(?!completa)",
        r"cassette",
        r"bielas",
        r"pedales",
        r"sillin",
        r"saddle",
    ]

    COMPLETE_BIKE_PATTERNS = [
        r"bicicleta\s+completa",
        r"full\s+bike",
        r"completa",
        r"lista\s+para\s+rodar",
        r"ready\s+to\s+ride",
        r"montada\s+completa",
        r"lista\s+para\s+montar",
    ]

    @staticmethod
    def check_url_availability(url: str) -> Tuple[bool, str]:
        """Check if URL is still available"""
        try:
            response = httpx.head(url, follow_redirects=True, timeout=5)

            if response.status_code == 404:
                return False, "LISTING_404_NOT_FOUND"
            elif response.status_code == 410:
                return False, "LISTING_410_GONE"
            elif response.status_code >= 500:
                return False, "LISTING_SERVER_ERROR"
            elif response.status_code >= 400:
                return False, f"LISTING_HTTP_{response.status_code}"
            else:
                return True, "LISTING_AVAILABLE"

        except Exception as e:
            logger.warning(f"URL check error: {e}")
            # If we can't verify, assume it's OK (avoid false negatives)
            return True, "LISTING_VERIFICATION_SKIPPED"

    @staticmethod
    async def check_url_availability_async(url: str) -> Tuple[bool, str]:
        """Async URL availability check"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.head(url, follow_redirects=True)

                if response.status_code == 404:
                    return False, "LISTING_404_NOT_FOUND"
                elif response.status_code == 410:
                    return False, "LISTING_410_GONE"
                elif response.status_code >= 500:
                    return False, "LISTING_SERVER_ERROR"
                elif response.status_code >= 400:
                    return False, f"LISTING_HTTP_{response.status_code}"
                else:
                    return True, "LISTING_AVAILABLE"

        except Exception as e:
            logger.warning(f"URL check error: {e}")
            return True, "LISTING_VERIFICATION_SKIPPED"

    @staticmethod
    def check_frame_only(title: str, description: str = "") -> Tuple[bool, Optional[str]]:
        """Check if listing is frame/parts only"""
        text = f"{title} {description}".lower()

        for pattern in AdvancedFilters.FRAME_ONLY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.debug(f"Frame only detected: {pattern}")
                return True, f"FRAME_ONLY_{pattern[:20]}"

        return False, None

    @staticmethod
    def check_parts_only(title: str, description: str = "") -> Tuple[bool, Optional[str]]:
        """Check if listing is parts only"""
        text = f"{title} {description}".lower()

        # Check for parts patterns
        parts_found = []
        for pattern in AdvancedFilters.PARTS_ONLY_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                parts_found.append(pattern[:20])

        # If multiple part indicators found, likely parts only
        if len(parts_found) >= 2:
            logger.debug(f"Parts only detected: {', '.join(parts_found)}")
            return True, f"PARTS_ONLY_{parts_found[0]}"

        return False, None

    @staticmethod
    def check_complete_bike(title: str, description: str = "") -> float:
        """Check for complete bike indicators (boost confidence)"""
        text = f"{title} {description}".lower()

        matches = 0
        for pattern in AdvancedFilters.COMPLETE_BIKE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
                logger.debug(f"Complete bike indicator found: {pattern}")

        # Return confidence boost (0-10%)
        return min(matches * 5, 10)

    @staticmethod
    def verify_model_match(title: str, parsed_model: Dict) -> Tuple[float, Optional[str]]:
        """Verify AI parsed model matches title"""

        if not parsed_model:
            return 0.0, "MODEL_MISSING"

        title_lower = title.lower()
        brand = parsed_model.get("brand", "").lower()
        model = parsed_model.get("model", "").lower()

        # Exact match
        if brand and model:
            full_model = f"{brand} {model}"
            if full_model in title_lower:
                return 1.0, None  # Perfect match

        # Brand match
        if brand and brand in title_lower:
            return 0.8, None  # Good match

        # Model keyword match
        if model and len(model) > 3 and model in title_lower:
            return 0.7, None

        # No match found
        logger.debug(f"Model mismatch: Title={title[:50]}, Model={brand} {model}")
        return 0.3, "MODEL_MISMATCH"

    @staticmethod
    def apply_all_filters(
        title: str,
        description: str,
        url: str,
        parsed_model: Dict,
        current_confidence: float
    ) -> Tuple[bool, str, float]:
        """
        Apply all filters to a listing.

        Returns:
            (should_send: bool, rejection_reason: str, adjusted_confidence: float)
        """

        # FILTER 1: URL Availability
        url_ok, url_reason = AdvancedFilters.check_url_availability(url)
        if not url_ok:
            logger.debug(f"URL check failed: {url_reason}")
            return False, url_reason, current_confidence

        # FILTER 2: Frame Only
        is_frame_only, frame_reason = AdvancedFilters.check_frame_only(title, description)
        if is_frame_only:
            logger.debug(f"Frame only filter triggered: {frame_reason}")
            return False, frame_reason, current_confidence

        # FILTER 3: Parts Only
        is_parts_only, parts_reason = AdvancedFilters.check_parts_only(title, description)
        if is_parts_only:
            logger.debug(f"Parts only filter triggered: {parts_reason}")
            return False, parts_reason, current_confidence

        # FILTER 4: Model Verification
        model_match, model_reason = AdvancedFilters.verify_model_match(title, parsed_model)
        if model_match < 0.5:  # Low model confidence
            logger.debug(f"Model verification failed: {model_reason}")
            return False, model_reason, current_confidence

        # BOOST: Complete Bike Signals
        confidence_boost = AdvancedFilters.check_complete_bike(title, description)
        adjusted_confidence = min(current_confidence + confidence_boost, 100)

        logger.debug(f"All filters passed. Confidence: {current_confidence} → {adjusted_confidence}")
        return True, "PASSED_ALL_FILTERS", adjusted_confidence
