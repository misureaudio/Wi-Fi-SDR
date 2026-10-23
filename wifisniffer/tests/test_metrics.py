import numpy as np

import tests.synth as synth
import wifisniffer.metrics as m

FS = 6_048_000


def test_frame_powers_half_scale_sinusoid_is_minus_9_dbfs():
    t = np.arange(4 * m.FRAME) / FS
    x = (4096 * np.cos(2 * np.pi * 1e6 * t)).astype(np.complex64)
    p = m.frame_powers_dbfs(x)
    assert len(p) == 4
    # mean|x|^2 = A^2/2, A=4096 -> 10log10((4096^2/2)/8192^2) = 10log10(0.125) ~ -9.03
    assert np.allclose(p, -9.03, atol=0.1)


def test_noise_floor_tracks_sigma():
    x = synth.noise_iq(64 * m.FRAME, sigma=100.0, seed=1)
    rep = m.dwell_report([x])
    # E|z|^2 = 2*100^2 = 20000 -> 10log10(20000/8192^2) ~ -35.26 dBFS
    assert abs(rep["noise_dbfs"] - (-35.26)) < 0.5


def test_occupancy_recovers_duty_cycle():
    noise = synth.noise_iq(2 * m.FRAME, sigma=100.0, seed=2)
    burst = np.full(m.FRAME, 4000.0, dtype=np.complex64)
    x = np.concatenate([noise[:m.FRAME], burst, noise[m.FRAME:], burst])
    rep = m.dwell_report([x])
    assert 0.4 <= rep["occupancy"] <= 0.6


def test_dwell_report_empty():
    rep = m.dwell_report([])
    assert rep["n_samples"] == 0 and rep["occupancy"] is None
