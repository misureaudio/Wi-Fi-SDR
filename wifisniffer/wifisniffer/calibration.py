"""dBFS -> dBm calibration for the RSPdx.

The RSPdx does not publish an exact ADC full-scale-to-input mapping, so use a
known-source offset instead of a theoretical constant:

Procedure
---------
1. Connect a signal generator (or a transmitter of known power at a measured
   distance) to antenna port A, set a known power P_k dBm.
2. Run the sniffer on the generator's frequency, e.g.
   ``python -m wifisniffer.sniffer --band ah_eu --max-hops 20 --out data/cal.csv``
3. Take the median ``rssi_dbfs`` over the hops (the generator is continuous,
   so RSSI tracks its power), and compute:
   ``offset = P_k - median_rssi_dbfs``
4. From then on: ``dBm = dBFS + offset``.

The offset absorbs the whole chain (LNA, tuner, baseband gain, cable loss,
antenna factor) for the gain settings used during calibration. Recalibrate
if you change ``--lna`` / ``--gr`` or the antenna. The per-row ``gain_db``
column is the API-reported total system gain; the theoretical approximation
is ``dBm ~= dBFS + gain_db - FS_INPUT_DBM`` with FS_INPUT_DBM ~ 0 dBm
(RSPdx max input), good to a few dB for a first estimate.
"""
from __future__ import annotations

import statistics
from typing import Union


def compute_offset(known_power_dbm: float,
                   measured_dbfs: Union[float, list[float]]) -> float:
    """Offset (dB) to add to dBFS readings to get dBm at the antenna."""
    if isinstance(measured_dbfs, (list, tuple)):
        if not measured_dbfs:
            raise ValueError("need at least one measurement")
        m = float(statistics.median(measured_dbfs))
    else:
        m = float(measured_dbfs)
    return float(known_power_dbm) - m


def dbfs_to_dbm(dBFS: float, offset_db: float) -> float:
    return float(dBFS) + offset_db
