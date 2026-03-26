from enum import Enum


class RiskLevel(str, Enum):
    T0 = "t0"
    T1 = "t1"
    T2 = "t2"
    T3 = "t3"
    T4 = "t4"
    UNKNOWN = "unknown"

    @classmethod
    def from_str(cls, value: str) -> "RiskLevel":
        """从数据库原始字符串构造，兼容未知值."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


class WhoLevel(str, Enum):
    GROUP_1 = "Group 1"
    GROUP_2A = "Group 2A"
    GROUP_2B = "Group 2B"
    GROUP_3 = "Group 3"
    GROUP_4 = "Group 4"
    UNKNOWN = "Unknown"


class UnitValue(str, Enum):
    G = "g"
    MG = "mg"
    KJ = "kJ"
    KCAL = "kcal"
    ML = "mL"


class ReferenceType(str, Enum):
    PER_100_WEIGHT = "PER_100_WEIGHT"
    PER_100_ENERGY = "PER_100_ENERGY"
    PER_SERVING = "PER_SERVING"
    PER_DAY = "PER_DAY"


class ReferenceUnit(str, Enum):
    G = "g"
    MG = "mg"
    KCAL = "kcal"
    ML = "mL"
    KJ = "kJ"
    SERVING = "serving"
    DAY = "day"
