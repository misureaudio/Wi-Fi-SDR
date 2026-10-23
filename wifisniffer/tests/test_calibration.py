import wifisniffer.calibration as cal


def test_offset_from_known_source():
    # a -20 dBm generator reads -55 dBFS -> offset +35
    off = cal.compute_offset(known_power_dbm=-20.0, measured_dbfs=-55.0)
    assert off == 35.0


def test_roundtrip():
    off = cal.compute_offset(known_power_dbm=-30.0, measured_dbfs=-61.5)
    assert cal.dbfs_to_dbm(-61.5, off) == -30.0


def test_mean_over_multiple_measurements():
    off = cal.compute_offset(known_power_dbm=-20.0,
                             measured_dbfs=[-55.0, -54.8, -55.2])
    assert off == 35.0
