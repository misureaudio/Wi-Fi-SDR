"""Sub-GHz Wi-Fi channel tables and the IF-window hop planner (band-agnostic)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Channel:
    name: str
    center_hz: float
    bw_hz: float


def _band(prefix: str, start_hz: float, stop_hz: float, bw_hz: float) -> list[Channel]:
    """Contiguous channels of bw_hz packed from start_hz up to stop_hz."""
    out: list[Channel] = []
    center = start_hz + bw_hz / 2.0
    n = 0
    while center + bw_hz / 2.0 <= stop_hz + 1e-3:
        n += 1
        out.append(Channel(f"{prefix}{n}", center, bw_hz))
        center += bw_hz
    return out


# 802.11ah (HaLow) - EU: 863-868.6 MHz, 1 MHz channels
AH_EU = _band("ah-eu", 863.0e6, 868.6e6, 1.0e6)
# 802.11ah - US: 902-928 MHz, 1 MHz channels
AH_US = _band("ah-us", 902.0e6, 928.0e6, 1.0e6)
# 802.11af (TV white space) - demo subset, 5 MHz channels (real plan is region/DB dependent)
AF_DEMO = [
    Channel("af-1", 505.5e6, 5.0e6),
    Channel("af-2", 510.5e6, 5.0e6),
    Channel("af-3", 515.5e6, 5.0e6),
]

BANDS: dict[str, list[Channel]] = {
    "ah_eu": AH_EU,
    "ah_us": AH_US,
    "af_demo": AF_DEMO,
}


def hop_plan(channels: list[Channel], if_bw_hz: float) -> list[tuple[float, list[Channel]]]:
    """Greedy covering: the window's left edge aligns with the leftmost uncovered
    channel's left edge (maximizes rightward coverage).
    Returns list of (tune_center_hz, [channels fully inside the window])."""
    uncovered = list(channels)
    plan: list[tuple[float, list[Channel]]] = []
    while uncovered:
        leftmost = min(uncovered, key=lambda c: c.center_hz)
        center = leftmost.center_hz - leftmost.bw_hz / 2.0 + if_bw_hz / 2.0
        lo, hi = center - if_bw_hz / 2.0, center + if_bw_hz / 2.0
        covered = [
            c for c in uncovered
            if c.center_hz - c.bw_hz / 2.0 >= lo - 1e-3
            and c.center_hz + c.bw_hz / 2.0 <= hi + 1e-3
        ]
        plan.append((center, covered))
        uncovered = [c for c in uncovered if c not in covered]
    return plan
