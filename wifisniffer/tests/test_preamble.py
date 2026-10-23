import numpy as np

import tests.synth as synth
import wifisniffer.preamble as p

FS = 6_048_000
SP = 312_500.0


def test_fires_on_synthetic_ah_lstf():
    x = synth.ah_lstf_iq(65536, FS, spacing=SP, noise_db=30, seed=0)
    assert p.lstf_comb_metric(x, FS, spacing_hz=SP) > 12.0


def test_quiet_on_pure_noise():
    x = synth.noise_iq(65536, sigma=300.0, seed=1)
    assert p.lstf_comb_metric(x, FS, spacing_hz=SP) < 6.0


def test_quiet_on_single_tone_at_one_comb_line():
    # narrowband interferer on the k=4 line only -> no comb structure
    t = np.arange(65536) / FS
    x = (3000 * np.exp(2j * np.pi * 4 * SP * t)).astype(np.complex64)
    x = x + synth.noise_iq(65536, sigma=300.0, seed=2)
    assert p.lstf_comb_metric(x, FS, spacing_hz=SP) < 6.0


def test_wrong_spacing_does_not_fire():
    x = synth.ah_lstf_iq(65536, FS, spacing=SP, noise_db=30, seed=3)
    assert p.lstf_comb_metric(x, FS, spacing_hz=1_250_000.0) < 12.0


def test_detect_preambles_counts_chunks():
    x = synth.ah_lstf_iq(8 * 65536, FS, spacing=SP, noise_db=30, seed=4)
    r = p.detect_preambles([x], FS, spacing_hz=SP, threshold_db=12.0, chunk_s=0.016)
    assert r["preamble_count"] >= 2
    assert r["comb_peak_db"] > 12.0
