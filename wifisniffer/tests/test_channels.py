import wifisniffer.channels as ch


def test_ah_eu_five_one_mhz_channels():
    assert len(ch.AH_EU) == 5
    assert all(c.bw_hz == 1e6 for c in ch.AH_EU)
    assert all(863e6 <= c.center_hz <= 868.6e6 for c in ch.AH_EU)
    assert ch.AH_EU[0].center_hz == 863.5e6


def test_ah_us_26_one_mhz_channels():
    assert len(ch.AH_US) == 26
    assert ch.AH_US[0].center_hz == 902.5e6
    assert ch.AH_US[-1].center_hz == 927.5e6


def test_hop_plan_eu_single_tune_covers_whole_band():
    plan = ch.hop_plan(ch.AH_EU, 6e6)
    assert len(plan) == 1
    assert len(plan[0][1]) == 5
    assert plan[0][0] == 866.0e6  # window 863.0-869.0 MHz


def test_hop_plan_us_full_coverage_each_channel_in_window():
    plan = ch.hop_plan(ch.AH_US, 6e6)
    covered = [c for _, cs in plan for c in cs]
    assert len(covered) == 26
    for center, cs in plan:
        for c in cs:
            assert c.center_hz - c.bw_hz / 2 >= center - 3e6 - 1e-3
            assert c.center_hz + c.bw_hz / 2 <= center + 3e6 + 1e-3
