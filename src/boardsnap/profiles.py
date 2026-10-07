"""Small, explicit profiles; adding a theme requires data and a measured report."""

from dataclasses import dataclass
from typing import Literal


DEFAULT_PROFILE = "lichess-cburnett-brown-v1"


@dataclass(frozen=True)
class Profile:
    id: str
    colors: tuple[tuple[int, int, int], tuple[int, int, int]]
    coordinates: str
    piece_asset: str
    coordinate_asset: str
    color_tolerance: int = 12
    kind: Literal["digital", "print"] = "digital"
    experimental: bool = False


PROFILES = {
    DEFAULT_PROFILE: Profile(DEFAULT_PROFILE, ((240, 217, 181), (181, 136, 99)),
                             "lichess", "piece-templates", "coordinate-glyphs"),
    "lichess-cburnett-blue-v1": Profile(
        "lichess-cburnett-blue-v1", ((222, 227, 230), (140, 162, 173)),
        "lichess", "lichess-cburnett-blue-v1-pieces", "lichess-cburnett-blue-v1-coordinates", 5),
    "chesscom-default-green-v1": Profile(
        "chesscom-default-green-v1", ((235, 236, 208), (115, 149, 82)),
        "chesscom", "chesscom-default-green-v1-pieces", "chesscom-default-green-v1-coordinates", 5),
    "book-strategy-hatched-v1": Profile(
        "book-strategy-hatched-v1", ((255, 255, 255), (128, 128, 128)),
        "none", "book-strategy-hatched-v1-pieces", "", kind="print", experimental=True),
}


def get_profile(profile: str = DEFAULT_PROFILE) -> Profile:
    """Reject unknown profiles instead of silently applying another piece set."""
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError(f"Unknown recognition profile: {profile!r}")
    return PROFILES[profile]
