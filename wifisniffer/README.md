# wifisniffer — passive sub-GHz Wi-Fi sniffer for the SDRplay RSPdx

Passive receiver that hops sub-1 GHz Wi-Fi channels and logs, per hop:
RSSI, peak, noise floor, channel occupancy, and 802.11 L-STF preamble
detection (spectral line-comb metric) to CSV.

## Scope (important)

**The RSPdx tops out at 2 GHz — it cannot receive 2.4 GHz or 5 GHz Wi-Fi.**
Verified: SDRplay spec (1 kHz–2 GHz) and the official RSPdx plugin's hard
2 GHz frequency clamp. This sniffer targets the Wi-Fi bands the RSPdx *can*
receive:

| Band | Standard | Channels |
|---|---|---|
| 863–868.6 MHz (EU) | 802.11ah (HaLow) | `--band ah_eu`, 5 × 1 MHz |
| 902–928 MHz (US) | 802.11ah (HaLow) | `--band ah_us`, 26 × 1 MHz |
| 500–700 MHz | 802.11af (TV white space) | `--band af_demo` (demo subset) |

802.11ah/af deployments are rare; expect mostly quiet sub-GHz. Any 868/915
MHz ISM transmitter (Zigbee etc.) is a fine real-signal sanity check.

For 2.4 GHz Wi-Fi you need different hardware (SDRplay RSP2 for sensing —
same API, device ID 2; HackRF One for full 20 MHz OFDM demod). The DSP core
is band-agnostic: add a channel table and switch `--spacing 1250000`
(see plan Task 11). For packet-level decode/decrypt use a monitor-mode
Wi-Fi NIC, not an SDR.

## Prerequisites

- SDRplay Hardware API v3 (≥ 3.15) installed; the **SDRplay service must be
  running**.
- Nothing else holding the RSPdx (SDR++/SDR#/SDRuno must be closed — device
  access is exclusive).
- Antenna on **port A (SMA)**: 868/915 MHz ¼-wave or a broadband whip.
- Python: `D:/Source/hermes-dir/.venv` (numpy, pytest).

## Run

```bat
cd /d D:\Source\hermes-dir\wifisniffer

:: EU 802.11ah, 6 hops, CSV + PSD snapshot
D:\Source\hermes-dir\.venv\Scripts\python.exe -m wifisniffer.sniffer --band ah_eu --max-hops 6 --out data/ah_eu.csv --psd-dir data

:: US 802.11ah (5 hops of 6 MHz windows over 902-928 MHz)
D:\Source\hermes-dir\.venv\Scripts\python.exe -m wifisniffer.sniffer --band ah_us --dwell 0.5

:: Hardware smoke test (6 hops, writes data/smoke.csv)
D:\Source\hermes-dir\.venv\Scripts\python.exe scripts\hw_smoke.py

:: Unit tests (no hardware needed)
D:\Source\hermes-dir\.venv\Scripts\python.exe -m pytest tests -v
```

Key options (`--help` for all): `--fs 6.048` (MSPS; ≤6.048 for 14-bit),
`--bw 6000` (IF kHz), `--lna 8` (LNA state; 420–1000 MHz band: state 8 = 31 dB),
`--gr 40` (baseband gain reduction, 20 = max gain … 59 = max attenuation),
`--antenna 0|1|2` (A/B/C — C is <200 MHz only), `--spacing 312500` (L-STF comb
spacing, Hz), `--threshold 12` (comb metric threshold, dB).

## Output

CSV columns:

| Column | Meaning |
|---|---|
| `ts` | UTC timestamp |
| `center_hz` | tuner center frequency |
| `channels` | channel names inside the IF window |
| `n_samples` | IQ samples collected in the dwell |
| `rssi_dbfs` | mean level over the dwell (dBFS, full scale = 8192, uncalibrated) |
| `peak_dbfs` | peak 2048-sample frame power |
| `noise_dbfs` | median frame power (robust noise-floor estimate) |
| `occupancy` | fraction of frames above noise + 6 dB (0..1) |
| `preamble_count` | 32 ms slices with comb metric > threshold |
| `comb_peak_db` | best L-STF line-comb metric in the dwell (dB) |
| `gain_db` | total system gain from the last GainChange event |
| `overload_events` | power-overload events (auto-ACKed); raise `--gr` if > 0 |

A PSD snapshot (`psd_<freq>Hz.npz` with `freqs`, `psd`) is written on the
first hop when `--psd-dir` is given — use it to check the antenna is seeing
anything at all.

Interpretation: occupancy is a fraction-of-time metric (frame = 2048 samples
≈ 0.34 ms); the comb metric is the median power of the L-STF spectral lines
at ±k·312.5 kHz relative to the continuum — a real 802.11ah preamble drives
it well above 12 dB, noise stays near 0 dB.

## Tuning guide

- Clipped readings (rssi_dbfs near 0, `overload_events` > 0): raise `--gr`
  (e.g. 50) or add an external pad; 0 dBm max input.
- Noise floor too high / nothing visible: lower `--gr` and/or raise `--lna`
  (state 13 = 46 dB in the 420–1000 MHz band).
- dBFS → dBm: see `wifisniffer/calibration.py` (known-source method); the
  `gain_db` column is the system gain term.

## Legal

Passive reception only (the RSPdx is receive-only). Observe local regulations
regarding monitoring.
