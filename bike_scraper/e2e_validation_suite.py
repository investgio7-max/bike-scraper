"""
End-to-End Validation Suite

Проверяет полную цепочку системы на реальных объявлениях Wallapop:
1. Price Extraction
2. Bike Parsing
3. Market Comparison
4. Deal Evaluation
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


class DealGrade(Enum):
    """Оценка выгодности сделки"""
    S = "S-Tier"      # Исключительная сделка (>30% дисконт)
    A = "A-Tier"      # Отличная сделка (20-30% дисконт)
    B = "B-Tier"      # Хорошая сделка (10-20% дисконт)
    C = "C-Tier"      # Нормальная цена (0-10% дисконт)
    D = "D-Tier"      # Дорого (отрицательный дисконт)
    F = "F-Tier"      # Явно перепроданная (>50% дороже)


@dataclass
class ParsedBike:
    """Результат парсинга названия велосипеда"""
    title: str
    brand: str = "Unknown"
    model: str = "Unknown"
    version: str = "Unknown"
    groupset: str = "Unknown"
    year: Optional[int] = None
    size: Optional[str] = None
    confidence: float = 0.0  # 0-100
    errors: List[str] = field(default_factory=list)


@dataclass
class PriceData:
    """Результат извлечения цены"""
    raw_text: str
    price: Optional[float] = None
    currency: str = "EUR"
    status: str = "UNKNOWN"  # VALID, INVALID, SUSPICIOUS
    confidence: float = 0.0  # 0-100
    errors: List[str] = field(default_factory=list)


@dataclass
class MarketComparison:
    """Результат сравнения с рынком"""
    market_price: Optional[float] = None
    comparable_count: int = 0
    confidence: float = 0.0  # 0-100
    search_radius: str = "unknown"
    similar_bikes: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass
class DealEvaluation:
    """Оценка выгодности сделки"""
    listing_price: float
    market_price: Optional[float] = None
    difference: Optional[float] = None  # market - listing
    discount_percent: Optional[float] = None  # (market - listing) / market * 100
    confidence: float = 0.0  # 0-100
    grade: DealGrade = DealGrade.C
    profit_potential: Optional[float] = None  # Potential resale profit
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate grade based on discount"""
        if self.market_price and self.discount_percent is not None:
            discount = self.discount_percent
            if discount > 30:
                self.grade = DealGrade.S
            elif discount > 20:
                self.grade = DealGrade.A
            elif discount > 10:
                self.grade = DealGrade.B
            elif discount > 0:
                self.grade = DealGrade.C
            elif discount > -30:
                self.grade = DealGrade.D
            else:
                self.grade = DealGrade.F


@dataclass
class ListingValidation:
    """Полная валидация одного объявления"""
    listing_id: str
    url: str
    title: str

    # Components
    parsed_bike: ParsedBike = field(default_factory=lambda: ParsedBike(""))
    price_data: PriceData = field(default_factory=lambda: PriceData(""))
    market_comparison: MarketComparison = field(default_factory=MarketComparison)
    deal_evaluation: DealEvaluation = field(default_factory=lambda: DealEvaluation(0))

    # Overall stats
    total_errors: int = 0
    validation_score: float = 0.0  # 0-100


class E2EValidator:
    """End-to-End Validation Engine"""

    def __init__(self):
        self.validations: List[ListingValidation] = []
        self.error_summary: Dict[str, int] = {}

    def add_validation(self, validation: ListingValidation):
        """Add a validation result"""
        self.validations.append(validation)
        self._update_error_summary(validation)

    def _update_error_summary(self, validation: ListingValidation):
        """Track errors by type"""
        total_errors = (
            len(validation.parsed_bike.errors) +
            len(validation.price_data.errors) +
            len(validation.market_comparison.errors) +
            len(validation.deal_evaluation.errors)
        )
        validation.total_errors = total_errors

        # Categorize errors
        for error in validation.parsed_bike.errors:
            key = f"Parse: {error.split(':')[0] if ':' in error else error}"
            self.error_summary[key] = self.error_summary.get(key, 0) + 1

        for error in validation.price_data.errors:
            key = f"Price: {error.split(':')[0] if ':' in error else error}"
            self.error_summary[key] = self.error_summary.get(key, 0) + 1

        for error in validation.market_comparison.errors:
            key = f"Market: {error.split(':')[0] if ':' in error else error}"
            self.error_summary[key] = self.error_summary.get(key, 0) + 1

        for error in validation.deal_evaluation.errors:
            key = f"Deal: {error.split(':')[0] if ':' in error else error}"
            self.error_summary[key] = self.error_summary.get(key, 0) + 1

    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        if not self.validations:
            return {}

        total = len(self.validations)
        with_errors = sum(1 for v in self.validations if v.total_errors > 0)
        error_rate = (with_errors / total * 100) if total > 0 else 0

        # Price validation stats
        valid_prices = sum(
            1 for v in self.validations
            if v.price_data.status == "VALID"
        )
        suspicious_prices = sum(
            1 for v in self.validations
            if v.price_data.status == "SUSPICIOUS"
        )
        invalid_prices = sum(
            1 for v in self.validations
            if v.price_data.status == "INVALID"
        )

        # Deal grades
        grade_counts = {}
        for grade in DealGrade:
            grade_counts[grade.value] = sum(
                1 for v in self.validations
                if v.deal_evaluation.grade == grade
            )

        # Market comparison coverage
        with_comparables = sum(
            1 for v in self.validations
            if v.market_comparison.comparable_count > 0
        )

        # Avg prices
        listing_prices = [
            v.deal_evaluation.listing_price
            for v in self.validations
            if v.deal_evaluation.listing_price > 0
        ]
        market_prices = [
            v.deal_evaluation.market_price
            for v in self.validations
            if v.deal_evaluation.market_price and v.deal_evaluation.market_price > 0
        ]

        discounts = [
            v.deal_evaluation.discount_percent
            for v in self.validations
            if v.deal_evaluation.discount_percent is not None
        ]

        return {
            "total_listings": total,
            "with_errors": with_errors,
            "error_rate": error_rate,
            "valid_prices": valid_prices,
            "price_valid_rate": (valid_prices / total * 100) if total > 0 else 0,
            "suspicious_prices": suspicious_prices,
            "invalid_prices": invalid_prices,
            "grade_distribution": grade_counts,
            "listings_with_comparables": with_comparables,
            "comparable_coverage": (with_comparables / total * 100) if total > 0 else 0,
            "avg_listing_price": (
                statistics.mean(listing_prices) if listing_prices else None
            ),
            "avg_market_price": (
                statistics.mean(market_prices) if market_prices else None
            ),
            "avg_discount": (
                statistics.mean(discounts) if discounts else None
            ),
            "error_summary": self.error_summary,
        }

    def get_top_deals(self, n: int = 20) -> List[ListingValidation]:
        """Get top N best deals"""
        # Filter: must have price, market comparison, and discount
        valid_deals = [
            v for v in self.validations
            if (
                v.deal_evaluation.listing_price > 0 and
                v.deal_evaluation.market_price and
                v.deal_evaluation.discount_percent is not None and
                v.deal_evaluation.discount_percent > 0  # Positive discount only
            )
        ]

        # Sort by discount percent (descending)
        sorted_deals = sorted(
            valid_deals,
            key=lambda v: v.deal_evaluation.discount_percent or 0,
            reverse=True
        )

        return sorted_deals[:n]

    def get_errors_by_type(self) -> Dict[str, List[ListingValidation]]:
        """Get listings grouped by error type"""
        errors_dict = {}

        for validation in self.validations:
            if validation.total_errors == 0:
                continue

            # Parse errors
            for error in validation.parsed_bike.errors:
                error_type = f"Parse: {error.split(':')[0]}"
                if error_type not in errors_dict:
                    errors_dict[error_type] = []
                if validation not in errors_dict[error_type]:
                    errors_dict[error_type].append(validation)

            # Price errors
            for error in validation.price_data.errors:
                error_type = f"Price: {error.split(':')[0]}"
                if error_type not in errors_dict:
                    errors_dict[error_type] = []
                if validation not in errors_dict[error_type]:
                    errors_dict[error_type].append(validation)

            # Market errors
            for error in validation.market_comparison.errors:
                error_type = f"Market: {error.split(':')[0]}"
                if error_type not in errors_dict:
                    errors_dict[error_type] = []
                if validation not in errors_dict[error_type]:
                    errors_dict[error_type].append(validation)

            # Deal errors
            for error in validation.deal_evaluation.errors:
                error_type = f"Deal: {error.split(':')[0]}"
                if error_type not in errors_dict:
                    errors_dict[error_type] = []
                if validation not in errors_dict[error_type]:
                    errors_dict[error_type].append(validation)

        return errors_dict

    def get_readiness_score(self) -> Dict:
        """Assess system readiness for production"""
        stats = self.get_statistics()

        if not stats:
            return {"score": 0, "verdict": "NO DATA"}

        # Scoring criteria
        scores = {}

        # 1. Price extraction accuracy (40% weight)
        price_score = stats.get("price_valid_rate", 0)
        scores["price"] = price_score * 0.4

        # 2. Bike parsing accuracy (30% weight)
        # Assume ~90% if no major parse errors
        parse_errors = sum(
            1 for k, v in stats.get("error_summary", {}).items()
            if k.startswith("Parse:") and v > 2
        )
        parse_score = max(0, 90 - parse_errors * 10)
        scores["parsing"] = parse_score * 0.3

        # 3. Market comparison coverage (20% weight)
        market_score = stats.get("comparable_coverage", 0)
        scores["market"] = market_score * 0.2

        # 4. Deal identification quality (10% weight)
        # Good if we found S and A tier deals
        s_deals = stats.get("grade_distribution", {}).get("S-Tier", 0)
        a_deals = stats.get("grade_distribution", {}).get("A-Tier", 0)
        deal_score = min(100, (s_deals + a_deals) * 5)
        scores["deals"] = deal_score * 0.1

        total_score = sum(scores.values())

        # Determine readiness
        if total_score >= 80:
            verdict = "READY FOR PRODUCTION"
        elif total_score >= 60:
            verdict = "MOSTLY READY (REVIEW NEEDED)"
        elif total_score >= 40:
            verdict = "NEEDS IMPROVEMENT"
        else:
            verdict = "NOT READY"

        return {
            "overall_score": total_score,
            "component_scores": scores,
            "verdict": verdict,
        }


if __name__ == "__main__":
    # Demo
    validator = E2EValidator()

    # Create sample validation
    sample = ListingValidation(
        listing_id="123",
        url="https://example.com",
        title="Canyon Aeroad CF SLX 8 Di2 2022"
    )

    sample.parsed_bike = ParsedBike(
        title="Canyon Aeroad CF SLX 8 Di2 2022",
        brand="Canyon",
        model="Aeroad",
        version="CF SLX 8",
        groupset="Di2",
        year=2022
    )

    sample.price_data = PriceData(
        raw_text="€3,500",
        price=3500,
        status="VALID",
        confidence=95
    )

    sample.market_comparison = MarketComparison(
        market_price=4200,
        comparable_count=25,
        confidence=92
    )

    sample.deal_evaluation = DealEvaluation(
        listing_price=3500,
        market_price=4200,
        difference=700,
        discount_percent=16.7
    )

    validator.add_validation(sample)

    stats = validator.get_statistics()
    print(f"Stats: {stats}")

    readiness = validator.get_readiness_score()
    print(f"Readiness: {readiness}")
