"""Channel-hopping sniffer loop: tune -> dwell -> metrics + preambles -> CSV row."""
from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timezone

import numpy as np

from .channels import hop_plan
from .metrics import dwell_report, psd_dbfs
from .preamble import detect_preambles


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        return str(v)
    return f"{v:.3f}" if isinstance(v, float) else str(v)


class Sniffer:
    def __init__(self, source, channels, if_bw_hz: float, fs_hz: float,
                 dwell_s: float = 0.25, settle_s: float = 0.005,
                 fs_scale: float = 8192.0, occ_margin_db: float = 6.0,
                 comb_spacing_hz: float = 312_500.0, comb_threshold_db: float = 12.0,
                 out_csv: str | None = None, psd_dir: str | None = None, log=print):
        self.source = source
        self.channels = channels
        self.if_bw_hz = if_bw_hz
        self.fs_hz = fs_hz
        self.dwell_s = dwell_s
        self.settle_s = settle_s
        self.fs_scale = fs_scale
        self.occ_margin_db = occ_margin_db
        self.comb_spacing_hz = comb_spacing_hz
        self.comb_threshold_db = comb_threshold_db
        self.out_csv = out_csv
        self.psd_dir = psd_dir
        self.log = log
        self._plan = hop_plan(channels, if_bw_hz)

    def run(self, max_hops: int | None = None) -> None:
        hop = 0
        while max_hops is None or hop < max_hops:
            center, covered = self._plan[hop % len(self._plan)]
            self.source.tune(center)
            time.sleep(self.settle_s)  # let the tuner settle; early blocks are garbage
            t0 = time.monotonic()
            blocks: list[np.ndarray] = []
            while time.monotonic() - t0 < self.dwell_s:
                b = self.source.read(timeout_s=0.05)
                if b is not None:
                    blocks.append(b)
            if hop == 0 and self.psd_dir and blocks:
                self._write_psd(center, blocks)
            rep = dwell_report(blocks, self.fs_scale, self.occ_margin_db)
            pre = detect_preambles(blocks, self.fs_hz, self.comb_spacing_hz,
                                   self.comb_threshold_db)
            row = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "center_hz": f"{center:.0f}",
                "channels": ",".join(c.name for c in covered),
                "n_samples": rep["n_samples"],
                "rssi_dbfs": _fmt(rep["rssi_dbfs"]),
                "peak_dbfs": _fmt(rep["peak_dbfs"]),
                "noise_dbfs": _fmt(rep["noise_dbfs"]),
                "occupancy": _fmt(rep["occupancy"]),
                "preamble_count": pre["preamble_count"],
                "comb_peak_db": _fmt(pre["comb_peak_db"]),
                "gain_db": _fmt(getattr(self.source, "last_gain_db", None)),
                "overload_events": getattr(self.source, "overload_events", 0),
            }
            self._write(row)
            self.log(row)
            hop += 1

    def _write_psd(self, center: float, blocks: list[np.ndarray]) -> None:
        assert self.psd_dir is not None  # callers guard on self.psd_dir
        os.makedirs(self.psd_dir, exist_ok=True)
        iq = np.concatenate(blocks)
        freqs, psd = psd_dbfs(iq, self.fs_hz)
        if len(psd) == 0:
            return
        path = os.path.join(self.psd_dir, f"psd_{int(center)}Hz.npz")
        np.savez(path, freqs=freqs, psd=psd)
        pk = int(np.argmax(psd))
        self.log({"psd_snapshot": path, "psd_peak_hz": float(freqs[pk]),
                  "psd_peak_dbfshz": _fmt(float(psd[pk]))})

    def _write(self, row: dict) -> None:
        if not self.out_csv:
            return
        new = not os.path.exists(self.out_csv)
        parent = os.path.dirname(self.out_csv)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.out_csv, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row.keys()))
            if new:
                w.writeheader()
            w.writerow(row)


def main(argv: list[str] | None = None) -> int:
    import argparse

    from . import api
    from .channels import BANDS
    from .device import SdrplaySession

    ap = argparse.ArgumentParser(prog="wifisniffer",
                                 description="Sub-GHz Wi-Fi sniffer (SDRplay RSPdx, API v3)")
    ap.add_argument("--band", choices=sorted(BANDS), default="ah_eu")
    ap.add_argument("--dwell", type=float, default=0.25, help="seconds per hop (default 0.25)")
    ap.add_argument("--fs", type=float, default=6.048,
                    help="sample rate MSPS (<=6.048 for 14-bit; default 6.048)")
    ap.add_argument("--bw", type=int, default=6000,
                    help="IF bandwidth kHz: 200/300/600/1536/5000/6000/7000/8000")
    ap.add_argument("--lna", type=int, default=8, help="LNA state (420-1000 MHz: 0..27)")
    ap.add_argument("--gr", type=int, default=40, help="baseband gain reduction dB, 20..59")
    ap.add_argument("--antenna", type=int, default=api.RSPDX_ANT_A, choices=[0, 1, 2])
    ap.add_argument("--spacing", type=float, default=312_500.0,
                    help="L-STF comb spacing Hz (312500 = ah 1 MHz; 1250000 = g/n 20 MHz)")
    ap.add_argument("--threshold", type=float, default=12.0, help="comb metric threshold dB")
    ap.add_argument("--out", default=None, help="CSV output path")
    ap.add_argument("--psd-dir", default=None, help="write startup PSD snapshot here")
    ap.add_argument("--max-hops", type=int, default=None)
    args = ap.parse_args(argv)

    fs_hz = args.fs * 1e6
    channels = BANDS[args.band]
    with SdrplaySession(fs_hz=fs_hz, bw=args.bw, lna_state=args.lna, gr_db=args.gr,
                        antenna=args.antenna) as sess:
        print(f"API version {sess._api.version:.2f}, gain={sess.last_gain_db:.1f} dB", flush=True)
        s = Sniffer(sess, channels, args.bw * 1e3, fs_hz, dwell_s=args.dwell,
                    comb_spacing_hz=args.spacing, comb_threshold_db=args.threshold,
                    out_csv=args.out, psd_dir=args.psd_dir)
        try:
            s.run(max_hops=args.max_hops)
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
