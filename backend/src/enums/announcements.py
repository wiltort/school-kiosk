from enum import StrEnum


class AnnouncementKind(StrEnum):
    """Способ отображения объявления на киоске."""

    TICKER = "ticker"
    FEED = "feed"
    BOTH = "both"
