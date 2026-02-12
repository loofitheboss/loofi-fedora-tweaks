from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PluginMetadata:
    id: str                          # unique slug, e.g. "hardware"
    name: str                        # display name
    description: str                 # tooltip and breadcrumb text
    category: str                    # sidebar category group, e.g. "System"
    icon: str                        # unicode emoji or icon ref string
    badge: str                       # "recommended" | "advanced" | ""
    version: str = "1.0.0"          # plugin version string
    requires: tuple[str, ...] = ()   # dependency plugin IDs (tuple for hashability)
    compat: dict[str, Any] = field(  # {min_fedora: 38, de: ["gnome","kde"], ...}
        default_factory=dict
    )
    order: int = 100                 # sort order within category (lower = higher in list)
    enabled: bool = True             # default enabled state
    rating_average: float = 0.0      # marketplace aggregate rating
    rating_count: int = 0            # number of ratings
    review_count: int = 0            # number of written reviews
    verified_publisher: bool = False  # trusted publisher marker from signed index
    publisher_id: str = ""           # stable publisher identity key
    publisher_badge: str = ""        # UI badge name, e.g. "verified"


@dataclass(frozen=True)
class PublisherVerification:
    """Contract for publisher verification status in v27 marketplace flows."""
    verified: bool = False
    publisher_id: str = ""
    badge: str = ""
    signature: str = ""
    trust_chain: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, entry: dict[str, Any]) -> "PublisherVerification":
        """Parse publisher verification from nested or flat marketplace fields."""
        verification = entry.get("publisher_verification", {})
        if not isinstance(verification, dict):
            verification = {}

        trust_chain = verification.get("trust_chain", ())
        if isinstance(trust_chain, list):
            trust_chain = tuple(str(item) for item in trust_chain)
        elif isinstance(trust_chain, tuple):
            trust_chain = tuple(str(item) for item in trust_chain)
        else:
            trust_chain = ()

        return cls(
            verified=bool(verification.get("verified", entry.get("verified_publisher", False))),
            publisher_id=str(verification.get("publisher_id", entry.get("publisher_id", "")) or ""),
            badge=str(verification.get("badge", entry.get("publisher_badge", "")) or ""),
            signature=str(verification.get("signature", "") or ""),
            trust_chain=trust_chain,
        )


@dataclass(frozen=True)
class ReviewAggregate:
    """Contract for plugin rating/review aggregate in listing/detail surfaces."""
    average_rating: float = 0.0
    rating_count: int = 0
    review_count: int = 0
    breakdown: dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, entry: dict[str, Any]) -> "ReviewAggregate":
        """Parse rating/review aggregate from nested or legacy marketplace fields."""
        ratings = entry.get("ratings", {})
        if not isinstance(ratings, dict):
            ratings = {}

        breakdown = ratings.get("breakdown", {})
        if not isinstance(breakdown, dict):
            breakdown = {}

        return cls(
            average_rating=_to_float(ratings.get("average", entry.get("rating_average", 0.0))),
            rating_count=_to_int(ratings.get("count", entry.get("rating_count", 0))),
            review_count=_to_int(ratings.get("review_count", ratings.get("reviews", entry.get("review_count", 0)))),
            breakdown={_to_int(k): _to_int(v) for k, v in breakdown.items()},
        )


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class CompatStatus:
    compatible: bool
    reason: str = ""                 # human-readable reason if not compatible
    warnings: list[str] = field(default_factory=list)
