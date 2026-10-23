"""Per-dwell metrics: frame powers, RSSI, noise floor, occupancy, PSD (dBFS)."""
from __future__ import annotations

import numpy as np

FRAME = 2048          # samples per power frame (~0.34 ms @ 6.048 MSPS)
FULL_SCALE = 8192.0   # assumed 14-bit full scale; calibrate in Task 10


def frame_powers_dbfs(iq: np.ndarray, full_scale: float = FULL_SCALE) -> np.ndarray:
    """Mean power per FRAME-sample frame in dBFS (0 dBFS = full scale)."""
    n_frames = len(iq) // FRAME
    if n_frames == 0:
        return np.array([])
    f = iq[: n_frames * FRAME].reshape(n_frames, FRAME)
    re = f.real.astype(np.float64)
    im = f.imag.astype(np.float64)
    p = (re ** 2 + im ** 2).mean(axis=1)
    return 10.0 * np.log10(p / (full_scale ** 2) + 1e-12)


def dwell_report(blocks: list[np.ndarray], full_scale: float = FULL_SCALE,
                 occ_margin_db: float = 6.0) -> dict:
    """Aggregate one dwell's IQ blocks.

    occupancy = fraction of frames whose power exceeds the median (noise-floor)
    estimate by occ_margin_db - robust to bursty OFDM traffic.
    """
    if not blocks:
        return {"n_samples": 0, "rssi_dbfs": None, "peak_dbfs": None,
                "noise_dbfs": None, "occupancy": None}
    iq = np.concatenate(blocks)
    p = frame_powers_dbfs(iq, full_scale)
    noise = float(np.median(p))
    re = iq.real.astype(np.float64)
    im = iq.imag.astype(np.float64)
    total = float((re ** 2 + im ** 2).sum())
    rssi = float(10.0 * np.log10(total / (len(iq) * full_scale ** 2) + 1e-12))
    return {
        "n_samples": int(len(iq)),
        "rssi_dbfs": rssi,
        "peak_dbfs": float(p.max()),
        "noise_dbfs": noise,
        "occupancy": float(np.mean(p > noise + occ_margin_db)),
    }


def psd_dbfs(iq: np.ndarray, fs_hz: float, fft_len: int = 4096,
             full_scale: float = FULL_SCALE) -> tuple[np.ndarray, np.ndarray]:
    """Averaged PSD in dBFS/Hz (50%-overlap Hann windowing)."""
    if len(iq) < fft_len:
        return np.array([]), np.array([])
    step = fft_len // 2
    n_seg = max(1, (len(iq) - fft_len) // step + 1)
    win = np.hanning(fft_len)
    acc = np.zeros(fft_len // 2 + 1)
    for s in range(n_seg):
        seg = iq[s * step: s * step + fft_len]
        if len(seg) < fft_len:
            break
        # numpy 2.x rfft rejects complex input: full fft, keep the rfft bin range
        acc += np.abs(np.fft.fft(seg * win)[: fft_len // 2 + 1]) ** 2
    acc /= n_seg
    freqs = np.fft.rfftfreq(fft_len, d=1.0 / fs_hz)
    psd = 10.0 * np.log10(acc / (full_scale ** 2 * fs_hz * (win ** 2).sum()) + 1e-18)
    return freqs, psd
