from enum import Enum

class Sorters(str, Enum):
    """Enum for review sorting options."""
    MOST_RELEVANT = "MOST_RELEVANT"
    NEWEST_FIRST = "NEWEST_FIRST"
    OLDEST_FIRST = "OLDEST_FIRST"
    HIGHEST_SCORE = "SCORE_DESC"
    LOWEST_SCORE = "SCORE_ASC"

class TimeOfYear(str, Enum):
    """Enum for time of year filter options."""
    ALL = "ALL"
    MAR_MAY = "_03_05"
    JUN_AUG = "_06_08"
    SEP_NOV = "_09_11"
    DEC_FEB = "_12_02"

class CustomerType(str, Enum):
    """Enum for customer type filter options."""
    ALL = "ALL"
    FAMILIES = "FAMILIES"
    COUPLES = "COUPLES"
    GROUP_OF_FRIENDS = "GROUP_OF_FRIENDS"
    SOLO_TRAVELLERS = "SOLO_TRAVELLERS"
    BUSINESS_TRAVELLERS = "BUSINESS_TRAVELLERS"

class ReviewScore(str, Enum):
    """Enum for review score filter options."""
    ALL = "ALL"
    WONDERFUL = "REVIEW_ADJ_SUPERB"
    GOOD = "REVIEW_ADJ_GOOD"
    FAIR = "REVIEW_ADJ_AVERAGE_PASSABLE"
    POOR = "REVIEW_ADJ_POOR"
    VERY_POOR = "REVIEW_ADJ_VERY_POOR"
