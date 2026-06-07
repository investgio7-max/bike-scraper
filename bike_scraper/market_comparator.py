"""
Market Comparator Module

Compare bike prices against ONLY the most similar comparable listings.
Never use generic brand/model medians - always find specific analogs.

Example:
- Search for: Canyon Aeroad CF SLX 8 Di2 2022 @ €3,500
- Compare with: Aeroad CF SLX 8 Di2 (2021-2023 only)
- Calculate: Market price based on 34 similar listings
- Result: €4,250 (17.6% discount)
"""

import re
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MatchType(Enum):
    """Type of match/comparison"""
    EXACT = 100  # All key attributes match
    VERY_SIMILAR = 90  # Brand + Model + Version + Groupset
    SIMILAR = 80  # Brand + Model + Groupset (different year)
    RELATED = 60  # Brand + Model (different version/groupset)
    FAMILY = 40  # Brand only (different model)
    FALLBACK = 20  # Last resort


@dataclass
class BikeComponents:
    """Extracted bike components from title"""
    brand: str  # Canyon, Trek, Specialized
    model: str  # Aeroad, Ultimate, Tarmac
    version: str  # CF SLX 8, CF SLX 7, etc
    groupset: str  # Di2, Mechanical, SRAM Red, etc
    year: Optional[int]  # 2022, 2023, etc
    wheelset: Optional[str]  # DT Swiss, Mavic, etc
    size: Optional[str]  # M, L, 56cm, etc
    title: str  # Original title

    @property
    def signature(self) -> str:
        """Create a unique signature for this bike"""
        return f"{self.brand}|{self.model}|{self.version}|{self.groupset}"


@dataclass
class ComparableResult:
    """Result of market comparison"""
    market_price: Optional[float]
    comparable_count: int
    confidence: int  # 0-100
    difference: Optional[float]  # market_price - listing_price
    discount_percent: Optional[float]  # percentage below market
    comparable_bikes: List[Dict] = None  # Similar listings used
    search_radius: str = "exact"  # exact, ±1 year, ±2 years, etc

    def __post_init__(self):
        if self.comparable_bikes is None:
            self.comparable_bikes = []


class BikeComponentExtractor:
    """Extract components from bike title"""

    BRANDS = {
        'canyon': 'Canyon',
        'trek': 'Trek',
        'specialized': 'Specialized',
        'giant': 'Giant',
        'scott': 'Scott',
        'orbea': 'Orbea',
        'colnago': 'Colnago',
        'pinarello': 'Pinarello',
        'bianchi': 'Bianchi',
        'focus': 'Focus',
        'cube': 'Cube',
        'merida': 'Merida',
    }

    MODELS = {
        'aeroad': 'Aeroad',
        'ultimate': 'Ultimate',
        'foil': 'Foil',
        'grail': 'Grail',
        'tarmac': 'Tarmac',
        'madone': 'Madone',
        'dogma': 'Dogma',
        'tomac': 'Tomac',
        'f12': 'F12',
        'speedmax': 'Speedmax',
        'topstone': 'Topstone',
        'fx': 'FX',
        'defy': 'Defy',
    }

    # Groupset BRANDS (main components)
    GROUPSET_BRANDS = [
        'sram red', 'sram force', 'sram rival', 'sram apex',  # Check longer first
        'dura-ace', 'ultegra', '105', 'tiagra',
        'campagnolo',
    ]

    # Groupset TYPES (transmission type)
    GROUPSET_TYPES = [
        'di2', 'axs', 'mechanical',
    ]

    GROUPSETS = [
        'dura-ace', 'ultegra', '105', 'tiagra',
        'sram red', 'sram force', 'sram rival', 'sram apex',
        'sram rival axs', 'sram force axs', 'sram red axs',
        'campagnolo',
        'di2', 'mechanical',
    ]

    WHEELSETS = [
        'dt swiss', 'mavic', 'campagnolo', 'fulcrum',
        'shimano', 'enve', 'zipp', 'reynolds',
    ]

    @staticmethod
    def extract(title: str) -> BikeComponents:
        """Extract components from bike title"""
        if not title:
            return None

        title_lower = title.lower()

        # Extract brand
        brand = "Unknown"
        for brand_key, brand_name in BikeComponentExtractor.BRANDS.items():
            if brand_key in title_lower:
                brand = brand_name
                break

        # Extract model
        model = "Unknown"
        for model_key, model_name in BikeComponentExtractor.MODELS.items():
            if model_key in title_lower:
                model = model_name
                break

        # Extract version (e.g., "CF SLX 8", "CF SL 7")
        version = BikeComponentExtractor._extract_version(title_lower)

        # Extract groupset
        groupset = BikeComponentExtractor._extract_groupset(title_lower)

        # Extract year
        year = BikeComponentExtractor._extract_year(title_lower)

        # Extract wheelset
        wheelset = BikeComponentExtractor._extract_wheelset(title_lower)

        # Extract size
        size = BikeComponentExtractor._extract_size(title_lower)

        return BikeComponents(
            brand=brand,
            model=model,
            version=version,
            groupset=groupset,
            year=year,
            wheelset=wheelset,
            size=size,
            title=title
        )

    @staticmethod
    def _extract_version(title: str) -> str:
        """Extract version like 'CF SLX 8', 'CF SL 7'"""
        # Pattern: CF SLX 8, CF SL 7, etc
        match = re.search(r'(cf\s+\w+\s*\d+|cp\s+\w+\s*\d+)', title)
        if match:
            return match.group(1).upper()
        return "Standard"

    @staticmethod
    def _extract_groupset(title: str) -> str:
        """
        Extract FULL groupset with type: 'Ultegra Di2', 'SRAM Red AXS', '105 Mechanical'

        Strategy:
        1. Find groupset brand (Ultegra, SRAM Red, Campagnolo, etc.)
        2. Find transmission type (Di2, AXS, Mechanical)
        3. Combine them: "Brand Type" or just "Brand" if no type found
        """
        # Extract groupset brand (check longer ones first)
        groupset_brand = None
        for brand in BikeComponentExtractor.GROUPSET_BRANDS:
            if brand in title:
                groupset_brand = brand.title()
                break

        if not groupset_brand:
            return "Unknown"

        # Extract transmission type (Di2, AXS, Mechanical)
        transmission_type = None
        for trans_type in BikeComponentExtractor.GROUPSET_TYPES:
            if trans_type in title:
                transmission_type = trans_type.title()
                break

        # Combine brand + type
        if transmission_type:
            # Special case: SRAM uses "AXS" but we already have it in the full name "SRAM Force AXS"
            # Don't double-add if it's already there
            if 'axs' in groupset_brand.lower():
                return groupset_brand  # "Sram Red Axs" is complete
            else:
                return f"{groupset_brand} {transmission_type}"  # "Ultegra Di2"
        else:
            return groupset_brand

    @staticmethod
    def _extract_year(title: str) -> Optional[int]:
        """Extract year like 2022, 2023"""
        match = re.search(r'\b(20\d{2})\b', title)
        if match:
            try:
                return int(match.group(1))
            except:
                return None
        return None

    @staticmethod
    def _extract_wheelset(title: str) -> Optional[str]:
        """Extract wheelset like 'DT Swiss', 'Mavic'"""
        for wheelset in BikeComponentExtractor.WHEELSETS:
            if wheelset in title:
                return wheelset.title()
        return None

    @staticmethod
    def _extract_size(title: str) -> Optional[str]:
        """Extract size like 'M', 'L', '56cm'"""
        match = re.search(r'\b([SMLXL]{1,2}|talla\s+\w+|size\s+\w+|\d{2}cm)\b', title, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None


class SimilarityScorer:
    """Calculate similarity score between two bikes"""

    # Weights for matching attributes
    # Based on actual market price impact analysis:
    # - Size: €0 impact → weight 5 (was 20)
    # - Groupset: €1800 range impact → weight 95 (was 80)
    # - Version: €900 range impact → weight 85 (was 90)
    # - Year: €900 range impact → weight 75 (was 70)
    # - Wheelset: minimal impact → weight 40 (was 50)
    # - Brand/Model: critical → weight 100 (unchanged)
    WEIGHTS = {
        'brand': 100,      # Critical - different brand = different type
        'model': 100,      # Critical - Aeroad vs Ultimate = huge difference
        'version': 85,     # €500 avg difference (was 90, overweighted)
        'groupset': 95,    # €1800 range difference (was 80, underweighted)
        'year': 75,        # €500-700 per year difference (was 70)
        'wheelset': 40,    # Minimal real impact (was 50)
        'size': 5,         # Zero price impact (was 20, highly overweighted)
    }

    @staticmethod
    def calculate_similarity(bike1: BikeComponents, bike2: BikeComponents) -> float:
        """
        Calculate similarity score (0-100) between two bikes.

        Both attributes must match to get points.
        """
        if not bike1 or not bike2:
            return 0

        total_score = 0
        total_possible = 0

        # Brand (100% match required)
        total_possible += SimilarityScorer.WEIGHTS['brand']
        if bike1.brand.lower() == bike2.brand.lower():
            total_score += SimilarityScorer.WEIGHTS['brand']

        # Model (100% match required)
        total_possible += SimilarityScorer.WEIGHTS['model']
        if bike1.model.lower() == bike2.model.lower():
            total_score += SimilarityScorer.WEIGHTS['model']

        # Version (90% weight)
        total_possible += SimilarityScorer.WEIGHTS['version']
        if bike1.version.lower() == bike2.version.lower():
            total_score += SimilarityScorer.WEIGHTS['version']

        # Groupset (80% weight)
        total_possible += SimilarityScorer.WEIGHTS['groupset']
        if bike1.groupset and bike2.groupset:
            if bike1.groupset.lower() == bike2.groupset.lower():
                total_score += SimilarityScorer.WEIGHTS['groupset']

        # Year (70% weight) - allow ±1 year
        total_possible += SimilarityScorer.WEIGHTS['year']
        if bike1.year and bike2.year:
            if abs(bike1.year - bike2.year) <= 1:
                total_score += SimilarityScorer.WEIGHTS['year']

        # Wheelset (50% weight)
        if bike1.wheelset and bike2.wheelset:
            total_possible += SimilarityScorer.WEIGHTS['wheelset']
            if bike1.wheelset.lower() == bike2.wheelset.lower():
                total_score += SimilarityScorer.WEIGHTS['wheelset']

        # Size (20% weight)
        if bike1.size and bike2.size:
            total_possible += SimilarityScorer.WEIGHTS['size']
            if bike1.size.lower() == bike2.size.lower():
                total_score += SimilarityScorer.WEIGHTS['size']

        if total_possible == 0:
            return 0

        return int(total_score / total_possible * 100)


class MarketComparator:
    """Find comparable listings and calculate market price"""

    # Minimum matching weight to be considered
    MIN_MATCH_THRESHOLD = 50  # At least 50% match

    # Minimum comparable listings at each level
    MIN_COMPARABLES = {
        'exact': 20,  # Exact match (all key attributes)
        'relaxed_year': 20,  # ±1 year
        'extended_year': 15,  # ±2 years
        'similar': 10,  # Different version but same model/groupset
    }

    @staticmethod
    def find_comparables(
        bike: BikeComponents,
        all_listings: List[Dict]  # List of bikes with: components, price
    ) -> ComparableResult:
        """
        Find the most similar comparable listings.

        Strategy:
        1. Find exact matches (Brand + Model + Version + Groupset)
        2. If < 20: expand to ±1 year
        3. If < 20: expand to ±2 years
        4. If < 20: relax groupset requirement
        5. Calculate market price from comparables
        """

        if not bike or not all_listings:
            return ComparableResult(
                market_price=None,
                comparable_count=0,
                confidence=0,
                difference=None,
                discount_percent=None,
                search_radius="none"
            )

        # Strategy 1: Exact match (Brand + Model + Version + Groupset + Year)
        exact_matches = [
            l for l in all_listings
            if MarketComparator._is_exact_match(bike, l['components'])
        ]

        if len(exact_matches) >= MarketComparator.MIN_COMPARABLES['exact']:
            return MarketComparator._calculate_market_price(
                bike, exact_matches, "exact", 95
            )

        # Strategy 2: Relax year (±1 year)
        relaxed_year_1 = [
            l for l in all_listings
            if MarketComparator._is_similar_match(bike, l['components'], year_range=1)
        ]

        if len(relaxed_year_1) >= MarketComparator.MIN_COMPARABLES['relaxed_year']:
            return MarketComparator._calculate_market_price(
                bike, relaxed_year_1, "±1 year", 85
            )

        # Strategy 3: Relax year more (±2 years)
        relaxed_year_2 = [
            l for l in all_listings
            if MarketComparator._is_similar_match(bike, l['components'], year_range=2)
        ]

        if len(relaxed_year_2) >= MarketComparator.MIN_COMPARABLES['extended_year']:
            return MarketComparator._calculate_market_price(
                bike, relaxed_year_2, "±2 years", 75
            )

        # Strategy 4: Relax groupset too
        similar_matches = [
            l for l in all_listings
            if MarketComparator._is_family_match(bike, l['components'])
        ]

        if len(similar_matches) >= MarketComparator.MIN_COMPARABLES['similar']:
            return MarketComparator._calculate_market_price(
                bike, similar_matches, "similar version", 60
            )

        # Fallback: Not enough comparables
        return ComparableResult(
            market_price=None,
            comparable_count=len(similar_matches),
            confidence=0,
            difference=None,
            discount_percent=None,
            search_radius="insufficient"
        )

    @staticmethod
    def _is_exact_match(bike1: BikeComponents, bike2: BikeComponents) -> bool:
        """Check if bikes match exactly (Brand + Model + Version + Groupset + Year)"""
        return (
            bike1.brand.lower() == bike2.brand.lower() and
            bike1.model.lower() == bike2.model.lower() and
            bike1.version.lower() == bike2.version.lower() and
            bike1.groupset.lower() == bike2.groupset.lower() and
            bike1.year and bike2.year and bike1.year == bike2.year
        )

    @staticmethod
    def _is_similar_match(bike1: BikeComponents, bike2: BikeComponents, year_range: int = 1) -> bool:
        """Check if bikes match with relaxed year constraint"""
        year_match = True
        if bike1.year and bike2.year:
            year_match = abs(bike1.year - bike2.year) <= year_range
        else:
            year_match = True  # Allow if year missing

        return (
            bike1.brand.lower() == bike2.brand.lower() and
            bike1.model.lower() == bike2.model.lower() and
            bike1.version.lower() == bike2.version.lower() and
            bike1.groupset.lower() == bike2.groupset.lower() and
            year_match
        )

    @staticmethod
    def _is_family_match(bike1: BikeComponents, bike2: BikeComponents) -> bool:
        """Check if bikes are in same family (Brand + Model)"""
        return (
            bike1.brand.lower() == bike2.brand.lower() and
            bike1.model.lower() == bike2.model.lower()
        )

    @staticmethod
    def _calculate_market_price(
        bike: BikeComponents,
        comparables: List[Dict],
        search_radius: str,
        base_confidence: int
    ) -> ComparableResult:
        """Calculate market price from comparable listings"""

        if not comparables:
            return ComparableResult(
                market_price=None,
                comparable_count=0,
                confidence=0,
                difference=None,
                discount_percent=None
            )

        prices = [c['price'] for c in comparables if c.get('price')]

        if not prices:
            return ComparableResult(
                market_price=None,
                comparable_count=len(comparables),
                confidence=0,
                difference=None,
                discount_percent=None
            )

        # Use median (resistant to outliers)
        prices_sorted = sorted(prices)
        median_price = prices_sorted[len(prices_sorted) // 2]

        # Confidence based on count
        confidence = min(base_confidence + len(comparables) // 5, 99)

        return ComparableResult(
            market_price=median_price,
            comparable_count=len(comparables),
            confidence=confidence,
            difference=None,  # Will calculate later
            discount_percent=None,
            comparable_bikes=comparables,
            search_radius=search_radius
        )
