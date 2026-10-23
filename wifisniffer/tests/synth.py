"""Synthetic IQ for hardware-free tests. All signals are complex64 with
int16-range amplitudes (the pipeline's native sample format)."""
from __future__ import annotations

import numpy as np

LSTF16 = np.array([1, -1, 1, 1, 1, -1, -1, 0, 1, -1, 1, -1, 1, 1, 1, 0])


def noise_iq(n: int, sigma: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(n) + 1j * rng.standard_normal(n)).astype(np.complex64) * sigma


def ah_lstf_iq(n: int, sr: float, spacing: float = 312_500.0, n_lines: int = 16,
               amp: float = 300.0, noise_db: float = 30.0, seed: int = 0) -> np.ndarray:
    """ZIF baseband with an L-STF-like line comb: conjugate-symmetric tones at
    +/-k*spacing (k=1..n_lines) + Gaussian noise noise_db below line amplitude."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / sr
    x = np.zeros(n, dtype=np.complex128)
    for k in range(1, n_lines + 1):
        f = k * spacing
        if f >= sr / 2:
            break
        ph = rng.uniform(0, 2 * np.pi)
        x += amp * np.exp(1j * (2 * np.pi * f * t + ph))
        x += amp * np.exp(-1j * (2 * np.pi * f * t + ph))
    x += noise_iq(n, amp * 10 ** (-noise_db / 20), seed + 1)
    return x.astype(np.complex64)
