import numpy as np

import tests.synth as synth
import wifisniffer.channels as ch
import wifisniffer.sniffer as sn


class FakeSource:
    """Duck-typed source: .tune(freq), .read(timeout), gain/overload attrs."""

    def __init__(self, block: np.ndarray, n_blocks: int | None = None):
        self.block = block
        self._left = n_blocks
        self.tunes: list[float] = []
        self.last_gain_db = 55.0
        self.overload_events = 0

    def tune(self, freq_hz: float) -> None:
        self.tunes.append(freq_hz)

    def read(self, timeout_s: float = 0.05) -> np.ndarray | None:
        if self._left is not None:
            self._left -= 1
            if self._left < 0:
                return None
        return self.block.copy()


def test_single_eu_hop_writes_csv_row(tmp_path):
    fs = 6_048_000
    block = synth.noise_iq(65536, sigma=300.0, seed=2)
    src = FakeSource(block, n_blocks=4)
    out = tmp_path / "t.csv"
    s = sn.Sniffer(src, ch.AH_EU, 6e6, fs, dwell_s=0.02, settle_s=0.0, out_csv=str(out))
    s.run(max_hops=1)
    assert src.tunes == [866_000_000.0]  # EU: one 6 MHz window at 866.0 MHz
    lines = out.read_text().strip().splitlines()
    assert len(lines) == 2
    header = lines[0].split(",")
    for col in ("ts", "center_hz", "channels", "rssi_dbfs", "noise_dbfs",
                "occupancy", "preamble_count", "comb_peak_db", "gain_db"):
        assert col in header
    assert "ah-eu1" in lines[1]


def test_us_band_full_cycle_covers_all_channels(tmp_path):
    fs = 6_048_000
    block = synth.noise_iq(16384, sigma=300.0, seed=3)
    src = FakeSource(block, n_blocks=2)
    n_hops = len(ch.hop_plan(ch.AH_US, 6e6))
    s = sn.Sniffer(src, ch.AH_US, 6e6, fs, dwell_s=0.01, settle_s=0.0)
    s.run(max_hops=n_hops)
    assert len(src.tunes) == n_hops == 5
    assert len(set(src.tunes)) == 5  # full cycle, no repeats
