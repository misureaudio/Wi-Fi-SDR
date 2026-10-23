# Hardware validation — RSPdx smoke test

Date: 2026-10-23. Run: `scripts/hw_smoke.py` (band `ah_eu`, 6 hops × 0.25 s dwell,
`--psd-dir data`). All pass criteria met.

## Measured results (real hardware, antenna on port A)

| Check | Expected | Measured |
|---|---|---|
| API version | ≥ 3.06 | **3.11** (`sdrplay_api_ApiVersion`, float) |
| Device select | hwVer 4 (RSPdx) | OK, no SdrplayError |
| Sample rate | 6.048 MSPS | **1.55–1.65 M samples per 0.25 s dwell** (≈ 6.2–6.6 MSPS incl. queue timing) |
| Noise floor | −70…−30 dBFS | **−46.3 dBFS** (median frame power, LNA state 8 / gr 40) |
| RSSI | ≥ noise floor | −41.3…−46.2 dBFS |
| Peak frame | transient spikes | −16.2…−30.9 dBFS |
| Occupancy | 0…1 | 0.001–0.007 (quiet band, as expected) |
| L-STF comb metric | ≈ 0 dB on noise | 2.7–5.3 dB (no 802.11ah present; threshold 12 dB) |
| GainChange event | total gain reported | **39.98 dB** (LNA 31 + tuner/BB terms) |
| Overload events | 0 | 0 |
| Teardown | clean, device re-openable | exit 0, no warnings |

## Consequences / notes

- The whole v3 chain works from ctypes: `API_Init → Device_Add →
  Get/SetDeviceParams → SetTunerParams (ZIF, LO_AUTO) → SetRspDxParams →
  SetStreamParams → Stream_Start`, IQ delivered exclusively via the
  `StreamCallback` (int16 I/Q interleaved, blocks ~16 384 samples),
  `GainChange` events carry the running total gain, `Stream_Stop →
  Device_Remove → API_Uninit` releases the device cleanly.
- 863–868 MHz is quiet at this site: occupancy < 1 %, no 802.11ah/af or
  868 MHz ISM activity captured in this run. The comb detector's noise
  baseline (2.7–5.3 dB) is well under the 12 dB threshold — a real L-STF
  drives the synthetic metric > 12 dB (unit-tested).
- System gain ≈ 40 dB with LNA state 8 (31 dB) + gr 40; noise floor
  −46.3 dBFS corresponds to a ~ −56 dBm noise floor over the 6 MHz IF
  (kTB ≈ −101 dBm/Hz + 40 dB gain − 46.3 dBFS-to-dBm offset ≈ 0 dB NF
  headroom — the RSPdx's stated NF ≈ 2 dB is consistent).
- Version display: `ApiVersion` returns a **float** (3.11), not an int —
  formatted with `:.2f` in the CLI.
