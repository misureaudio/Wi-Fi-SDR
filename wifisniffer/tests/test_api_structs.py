import ctypes as ct

import pytest

import wifisniffer.api as api


def test_device_params_is_three_pointers_x64():
    # { DevParamsT *; RxChannelParamsT *; RxChannelParamsT * }
    assert ct.sizeof(api.DeviceParamsT) == 24


def test_callback_fns_is_three_ptrs():
    assert ct.sizeof(api.CallbackFnsT) == 24


def test_rf_freq_layout():
    # { double rfHz; unsigned char syncUpdate; }
    assert api.RfFreqT.rfHz.offset == 0
    assert api.RfFreqT.syncUpdate.offset == 8
    assert ct.sizeof(api.RfFreqT) == 16


def test_gain_layout():
    # { int gRdB; ubyte LNAstate; ubyte syncUpdate; int minGr; GainValuesT gainVals; }
    assert api.GainT.gRdB.offset == 0
    assert api.GainT.LNAstate.offset == 4
    assert api.GainT.syncUpdate.offset == 5
    assert api.GainT.minGr.offset == 8
    assert api.GainT.gainVals.offset == 12
    assert ct.sizeof(api.GainT) == 24


def test_tuner_params_layout():
    # { int bwType; int ifType; int loMode; GainT gain; RfFreqT rfFreq; DcOffsetTunerT dc; }
    # gain ends at 36; RfFreqT is 8-aligned (double) -> rfFreq @40, dc @56, size 72
    assert api.TunerParamsT.bwType.offset == 0
    assert api.TunerParamsT.ifType.offset == 4
    assert api.TunerParamsT.loMode.offset == 8
    assert api.TunerParamsT.gain.offset == 12
    assert api.TunerParamsT.rfFreq.offset == 40
    assert api.TunerParamsT.dcOffsetTuner.offset == 56
    assert ct.sizeof(api.TunerParamsT) == 72


def test_rspdx_params_layout():
    # { ubyte hdrEnable; ubyte biasTEnable; int antennaSel; ubyte rfNotch; ubyte rfDabNotch; }
    assert api.RspDxParamsT.hdrEnable.offset == 0
    assert api.RspDxParamsT.biasTEnable.offset == 1
    assert api.RspDxParamsT.antennaSel.offset == 4
    assert api.RspDxParamsT.rfNotchEnable.offset == 8
    assert api.RspDxParamsT.rfDabNotchEnable.offset == 9


def test_stream_cb_params_layout():
    assert api.StreamCbParamsT.firstSampleNum.offset == 0
    assert api.StreamCbParamsT.numSamples.offset == 16
    assert ct.sizeof(api.StreamCbParamsT) == 20


def test_device_t_layout():
    # SerNo[64] @0, hwVer @64, tuner(int) @68, rspDuoMode(int) @72, valid @76,
    # rspDuoSampleFreq(double, 8-aligned) @80, dev(ptr) @88
    assert api.DeviceT.SerNo.offset == 0
    assert api.DeviceT.hwVer.offset == 64
    assert api.DeviceT.rspDuoSampleFreq.offset == 80
    assert api.DeviceT.dev.offset == 88


def test_agc_layout():
    # { AgcControlT enable(int); int setPoint_dBfs; ushort x4; int syncUpdate; }
    assert api.AgcT.enable.offset == 0
    assert api.AgcT.setPoint_dBfs.offset == 4
    assert api.AgcT.attack_ms.offset == 8
    assert api.AgcT.syncUpdate.offset == 16
    assert ct.sizeof(api.AgcT) == 20


def test_control_params_agc_offset():
    # { DcOffsetT(2, align 1) @0; DecimationT(3, align 1) @2; AgcT(20, align 4) @8; int adsbMode @28; }
    assert api.ControlParamsT.dcOffset.offset == 0
    assert api.ControlParamsT.decimation.offset == 2
    assert api.ControlParamsT.agc.offset == 8
    assert api.ControlParamsT.adsbMode.offset == 28
    assert ct.sizeof(api.ControlParamsT) == 32


def test_dev_params_key_offsets():
    # Fields we mutate: fsFreq.fsHz and rspDxParams must sit where C puts them.
    assert api.DevParamsT.ppm.offset == 0
    assert api.DevParamsT.fsFreq.offset == 8
    # rspDxParams is the last member; just assert it is 4-aligned and after samplesPerPkt
    assert api.DevParamsT.rspDxParams.offset % 4 == 0
    assert api.DevParamsT.rspDxParams.offset > api.DevParamsT.samplesPerPkt.offset


def test_find_dll_raises_when_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        api.find_dll(str(tmp_path / "nope.dll"))
