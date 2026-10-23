"""802.11 L-STF detection via its spectral line comb.

The L-STF is a repeating 16-chip sequence: 0.8 us period (802.11a/g 20 MHz ->
1.25 MHz comb spacing) or 3.2 us period (802.11ah 1 MHz, 4x scaled ->
312.5 kHz spacing). The comb is detectable in an FFT even when the RSPdx's
band-limited capture (<=8 MHz IF, <=10.66 MSPS) aliases the time-domain chips
- hence the frequency-domain detector.
"""
from __future__ import annotations

import numpy as np

AH_1MHZ_COMB_SPACING = 312_500.0    # 1/3.2 us - 802.11ah 1 MHz (4x scaled 802.11a)
G20MHZ_COMB_SPACING = 1_250_000.0   # 1/0.8 us - 802.11a/g/n 20 MHz (future RSP2 target)

_DEFAULT_FFT = 65536


def lstf_comb_metric(iq: np.ndarray, fs_hz: float, spacing_hz: float = AH_1MHZ_COMB_SPACING,
                     n_lines: int = 8, fft_len: int = _DEFAULT_FFT) -> float:
    """Median power of bins at +k*spacing (k=1..n_lines) vs median continuum
    power, in dB. High => L-STF present. -inf if the window is too short."""
    if len(iq) < fft_len:
        return float("-inf")
    x = (iq[:fft_len] * np.hanning(fft_len)).astype(np.complex128)
    # numpy 2.x rfft rejects complex input: full fft, keep the rfft bin range
    spec = np.abs(np.fft.fft(x)[: fft_len // 2 + 1]) ** 2
    df = fs_hz / fft_len
    idx = [int(round(k * spacing_hz / df)) for k in range(1, n_lines + 1)]
    idx = [i for i in idx if 2 <= i < len(spec) - 2]
    if len(idx) < 3:
        return float("-inf")
    lines = float(np.median(spec[idx]))
    mask = np.ones(len(spec), dtype=bool)
    for i in idx:
        mask[i - 2:i + 3] = False
    cont = float(np.median(spec[mask])) + 1e-12
    return float(10.0 * np.log10(lines / cont))


def detect_preambles(blocks: list[np.ndarray], fs_hz: float,
                     spacing_hz: float = AH_1MHZ_COMB_SPACING, threshold_db: float = 12.0,
                     chunk_s: float = 0.032) -> dict:
    """Scan the dwell in chunk_s slices; count slices above threshold."""
    iq = np.concatenate(blocks) if blocks else np.array([], dtype=np.complex64)
    chunk = max(8192, int(chunk_s * fs_hz))
    fft_len = min(_DEFAULT_FFT, chunk & ~4095)
    if len(iq) < fft_len:
        return {"preamble_count": 0, "comb_peak_db": float("-inf")}
    count, peak = 0, float("-inf")
    for s in range(0, len(iq) - fft_len + 1, chunk):
        m = lstf_comb_metric(iq[s:], fs_hz, spacing_hz, fft_len=fft_len)
        peak = max(peak, m)
        if m > threshold_db:
            count += 1
    return {"preamble_count": count, "comb_peak_db": float(peak)}
