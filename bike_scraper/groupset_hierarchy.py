"""
Groupset Hierarchy Engine

Учитывает иерархию и близость между группами передач.
Обеспечивает более точное сравнение с учетом:
- Производителя (Shimano, SRAM, Campagnolo)
- Линейки/серии (105, Ultegra, Dura-Ace)
- Типа transmission (Mechanical, Di2, AXS)
- Рыночного класса
"""

from enum import Enum
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class GroupsetBrand(Enum):
    """Производители групп передач"""
    SHIMANO = "shimano"
    SRAM = "sram"
    CAMPAGNOLO = "campagnolo"
    UNKNOWN = "unknown"


class TransmissionType(Enum):
    """Тип transmission системы"""
    MECHANICAL = "mechanical"  # Механическая
    ELECTRONIC = "electronic"  # Электронная (Di2, AXS)


class GroupsetLevel(Enum):
    """Уровень/серия группы"""
    # SHIMANO
    ENTRY = 1        # 105
    MID = 2          # Ultegra
    PREMIUM = 3      # Dura-Ace

    # SRAM equivalent
    RIVAL = 1        # Entry level
    FORCE = 2        # Mid level
    RED = 3          # Premium level

    # Campagnolo equivalent
    CHORUS = 1       # Entry
    RECORD = 2       # Mid
    SUPER_RECORD = 3 # Premium


class GroupsetComponent:
    """Компонент группы передач с полной иерархией"""

    def __init__(self, name: str, brand: GroupsetBrand, level: int, transmission: TransmissionType):
        """
        Args:
            name: Название группы (e.g., "Ultegra Di2")
            brand: Производитель
            level: Уровень иерархии (1-3)
            transmission: Тип (Mechanical/Electronic)
        """
        self.name = name
        self.brand = brand
        self.level = level
        self.transmission = transmission

    def __repr__(self):
        return f"{self.name}"

    @property
    def full_class(self) -> str:
        """Полный класс группы для кроссбренд сравнений"""
        # Нормализуем классы между брендами
        level_map = {
            1: "Entry",
            2: "Mid",
            3: "Premium"
        }
        trans_str = "Electronic" if self.transmission == TransmissionType.ELECTRONIC else "Mechanical"
        return f"{level_map[self.level]}-{trans_str}"


class GroupsetHierarchy:
    """Определение иерархии всех групп передач"""

    # SHIMANO Groupsets
    SHIMANO_105_MECHANICAL = GroupsetComponent("105 Mechanical", GroupsetBrand.SHIMANO, 1, TransmissionType.MECHANICAL)
    SHIMANO_105_DI2 = GroupsetComponent("105 Di2", GroupsetBrand.SHIMANO, 1, TransmissionType.ELECTRONIC)
    SHIMANO_ULTEGRA_MECHANICAL = GroupsetComponent("Ultegra Mechanical", GroupsetBrand.SHIMANO, 2, TransmissionType.MECHANICAL)
    SHIMANO_ULTEGRA_DI2 = GroupsetComponent("Ultegra Di2", GroupsetBrand.SHIMANO, 2, TransmissionType.ELECTRONIC)
    SHIMANO_DURA_ACE_MECHANICAL = GroupsetComponent("Dura-Ace Mechanical", GroupsetBrand.SHIMANO, 3, TransmissionType.MECHANICAL)
    SHIMANO_DURA_ACE_DI2 = GroupsetComponent("Dura-Ace Di2", GroupsetBrand.SHIMANO, 3, TransmissionType.ELECTRONIC)

    # SRAM Groupsets
    SRAM_RIVAL_MECHANICAL = GroupsetComponent("Rival Mechanical", GroupsetBrand.SRAM, 1, TransmissionType.MECHANICAL)
    SRAM_RIVAL_AXS = GroupsetComponent("Rival AXS", GroupsetBrand.SRAM, 1, TransmissionType.ELECTRONIC)
    SRAM_FORCE_MECHANICAL = GroupsetComponent("Force Mechanical", GroupsetBrand.SRAM, 2, TransmissionType.MECHANICAL)
    SRAM_FORCE_AXS = GroupsetComponent("Force AXS", GroupsetBrand.SRAM, 2, TransmissionType.ELECTRONIC)
    SRAM_RED_MECHANICAL = GroupsetComponent("Red Mechanical", GroupsetBrand.SRAM, 3, TransmissionType.MECHANICAL)
    SRAM_RED_AXS = GroupsetComponent("Red AXS", GroupsetBrand.SRAM, 3, TransmissionType.ELECTRONIC)

    # Campagnolo Groupsets
    CAMPAGNOLO_CHORUS_MECHANICAL = GroupsetComponent("Chorus Mechanical", GroupsetBrand.CAMPAGNOLO, 1, TransmissionType.MECHANICAL)
    CAMPAGNOLO_CHORUS_ELECTRONIC = GroupsetComponent("Chorus Electronic", GroupsetBrand.CAMPAGNOLO, 1, TransmissionType.ELECTRONIC)
    CAMPAGNOLO_RECORD_MECHANICAL = GroupsetComponent("Record Mechanical", GroupsetBrand.CAMPAGNOLO, 2, TransmissionType.MECHANICAL)
    CAMPAGNOLO_RECORD_ELECTRONIC = GroupsetComponent("Record Electronic", GroupsetBrand.CAMPAGNOLO, 2, TransmissionType.ELECTRONIC)
    CAMPAGNOLO_SUPER_RECORD_MECHANICAL = GroupsetComponent("Super Record Mechanical", GroupsetBrand.CAMPAGNOLO, 3, TransmissionType.MECHANICAL)
    CAMPAGNOLO_SUPER_RECORD_ELECTRONIC = GroupsetComponent("Super Record Electronic", GroupsetBrand.CAMPAGNOLO, 3, TransmissionType.ELECTRONIC)

    ALL_GROUPSETS = [
        # Shimano
        SHIMANO_105_MECHANICAL, SHIMANO_105_DI2,
        SHIMANO_ULTEGRA_MECHANICAL, SHIMANO_ULTEGRA_DI2,
        SHIMANO_DURA_ACE_MECHANICAL, SHIMANO_DURA_ACE_DI2,
        # SRAM
        SRAM_RIVAL_MECHANICAL, SRAM_RIVAL_AXS,
        SRAM_FORCE_MECHANICAL, SRAM_FORCE_AXS,
        SRAM_RED_MECHANICAL, SRAM_RED_AXS,
        # Campagnolo
        CAMPAGNOLO_CHORUS_MECHANICAL, CAMPAGNOLO_CHORUS_ELECTRONIC,
        CAMPAGNOLO_RECORD_MECHANICAL, CAMPAGNOLO_RECORD_ELECTRONIC,
        CAMPAGNOLO_SUPER_RECORD_MECHANICAL, CAMPAGNOLO_SUPER_RECORD_ELECTRONIC,
    ]


class GroupsetSimilarityCalculator:
    """Вычисление близости между двумя группами передач"""

    @staticmethod
    def calculate(gs1: GroupsetComponent, gs2: GroupsetComponent) -> int:
        """
        Вычисление similarity score (0-100) между двумя группами.

        Факторы:
        1. Производитель (Brand) - самый важный
        2. Уровень в иерархии (Level)
        3. Тип transmission (Mechanical vs Electronic)
        """

        # 1. ПОЛНОЕ СОВПАДЕНИЕ
        if gs1.name == gs2.name:
            return 100

        # 2. РАЗНЫЕ ПРОИЗВОДИТЕЛИ - базовый score
        if gs1.brand != gs2.brand:
            # Кроссбренд сравнение
            return GroupsetSimilarityCalculator._cross_brand_similarity(gs1, gs2)

        # 3. ОДИНАКОВЫЙ ПРОИЗВОДИТЕЛЬ
        # Базовый score зависит от разницы в уровне
        level_diff = abs(gs1.level - gs2.level)

        if level_diff == 0:
            # Одинаковый уровень, разный тип transmission
            return GroupsetSimilarityCalculator._same_level_different_transmission(gs1, gs2)
        elif level_diff == 1:
            # Соседний уровень (105 vs Ultegra, Ultegra vs Dura-Ace)
            return GroupsetSimilarityCalculator._adjacent_level(gs1, gs2)
        else:  # level_diff >= 2
            # Разные уровни (105 vs Dura-Ace)
            return GroupsetSimilarityCalculator._distant_level(gs1, gs2)

    @staticmethod
    def _same_level_different_transmission(gs1: GroupsetComponent, gs2: GroupsetComponent) -> int:
        """Одинаковый уровень, но разный тип transmission"""
        # Ultegra Di2 vs Ultegra Mechanical → 85
        return 85

    @staticmethod
    def _adjacent_level(gs1: GroupsetComponent, gs2: GroupsetComponent) -> int:
        """Соседний уровень в иерархии"""
        # Соседний уровень (Ultegra-Dura-Ace, 105-Ultegra и т.д.)
        # Близость зависит только от типа transmission, не от направления

        if gs1.transmission == gs2.transmission:
            return 92  # Ultegra Di2 vs Dura-Ace Di2 (соседние, одинаковый тип)
        else:
            return 85  # Ultegra Di2 vs Dura-Ace Mechanical (соседние, разные типы)

    @staticmethod
    def _distant_level(gs1: GroupsetComponent, gs2: GroupsetComponent) -> int:
        """Разные уровни (более чем на 1)"""
        # 105 vs Dura-Ace → очень низкое совпадение
        if gs1.transmission == gs2.transmission:
            return 65  # Одинаковый тип, но сильно разные уровни
        else:
            return 60  # Разные типы и разные уровни

    @staticmethod
    def _cross_brand_similarity(gs1: GroupsetComponent, gs2: GroupsetComponent) -> int:
        """Сравнение между разными производителями"""

        # Правило 1: Одинаковый рыночный класс (Entry, Mid, Premium)
        # 105 ≈ Rival, Ultegra ≈ Force, Dura-Ace ≈ Red
        level_match = (gs1.level == gs2.level)
        transmission_match = (gs1.transmission == gs2.transmission)

        if level_match and transmission_match:
            # Один и тот же класс, одинаковый тип (ИДЕАЛЬНО для cross-brand)
            # 105 Di2 vs Rival AXS → 85 (Entry level, electronic)
            # Dura-Ace Di2 vs Red AXS → 95 (Premium level, electronic)
            # Ultegra Di2 vs Force AXS → 85 (Mid level, electronic)
            if gs1.level == 3:  # Premium vs Premium
                return 95
            else:  # Entry or Mid vs Entry/Mid
                return 85
        elif level_match and not transmission_match:
            # Один и тот же класс, но разные типы
            # 105 Di2 vs Rival Mechanical → 80 (Entry level, different transmission)
            # Dura-Ace Di2 vs Red Mechanical → 90 (Premium level, different transmission)
            if gs1.level == 3:  # Premium level, different transmission
                return 90
            else:  # Entry or Mid level, different transmission
                return 80
        elif not level_match and transmission_match:
            # Разные классы, одинаковый тип
            if abs(gs1.level - gs2.level) == 1:
                # Соседние классы (Mid vs Premium, Entry vs Mid), одинаковый тип
                # Ultegra Di2 vs Red AXS → 95 (Mid vs Premium electronic)
                # 105 Di2 vs Force AXS → 85 (Entry vs Mid electronic)
                if (gs1.level == 2 and gs2.level == 3) or (gs1.level == 3 and gs2.level == 2):
                    return 95  # Mid vs Premium with same transmission
                else:
                    # Entry vs Mid with same transmission
                    return 85
            else:
                # Дальние классы (Entry vs Premium), одинаковый тип
                # 105 Di2 vs Red AXS → 70 (Entry vs Premium, both electronic)
                return 70
        else:
            # Разные классы и разные типы - самое слабое совпадение
            if abs(gs1.level - gs2.level) == 1:
                return 55  # Соседние классы, разные типы
            else:
                return 50  # Далекие классы, разные типы


class GroupsetSimilarityMatrix:
    """Матрица близости для всех пар групп"""

    def __init__(self):
        self.groupsets = GroupsetHierarchy.ALL_GROUPSETS
        self.matrix: Dict[Tuple[str, str], int] = {}
        self._compute_matrix()

    def _compute_matrix(self):
        """Вычислить матрицу для всех пар"""
        for gs1 in self.groupsets:
            for gs2 in self.groupsets:
                key = (gs1.name, gs2.name)
                score = GroupsetSimilarityCalculator.calculate(gs1, gs2)
                self.matrix[key] = score

    def get_similarity(self, gs1_name: str, gs2_name: str) -> Optional[int]:
        """Получить similarity score между двумя группами по названию"""
        return self.matrix.get((gs1_name, gs2_name))

    def get_all_comparisons(self) -> list:
        """Получить все пары с их scores"""
        result = []
        seen = set()
        for (gs1_name, gs2_name), score in sorted(self.matrix.items()):
            # Избегаем дублей (A vs B и B vs A)
            pair_key = tuple(sorted([gs1_name, gs2_name]))
            if pair_key not in seen:
                seen.add(pair_key)
                result.append({
                    'groupset_a': gs1_name,
                    'groupset_b': gs2_name,
                    'score': score
                })
        return result


if __name__ == "__main__":
    # Test
    gs1 = GroupsetHierarchy.SHIMANO_ULTEGRA_DI2
    gs2 = GroupsetHierarchy.SHIMANO_105_MECHANICAL

    score = GroupsetSimilarityCalculator.calculate(gs1, gs2)
    print(f"{gs1.name} vs {gs2.name} = {score}/100")
