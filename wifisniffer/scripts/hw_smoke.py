"""Manual hardware smoke test (NOT run in CI).

Run:
  D:/Source/hermes-dir/.venv/Scripts/python.exe scripts/hw_smoke.py

Pass criteria:
  1. "API version 3.x" printed (x >= 15) with no SdrplayError.
  2. Six CSV rows written, noise_dbfs in roughly -70..-30 dBFS with an antenna
     (clipped/noise-floor-only readings => check antenna port A, LNA/gain).
  3. Clean exit; no WARNING line.
  4. SDRplay device immediately re-openable in SDR++ (exclusive access released).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wifisniffer.sniffer import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main([
        "--band", "ah_eu",
        "--max-hops", "6",
        "--out", os.path.join("data", "smoke.csv"),
        "--psd-dir", "data",
    ]))
