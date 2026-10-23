"""ctypes bindings for the SDRplay Hardware API v3 (RSPdx).

Transcribed from the SDRplay API Specification v3.15 (sdrplay.com) and
cross-checked against SDRplay/examples/sdrplay_api_example.c. Struct layout is
asserted in tests/test_api_structs.py - if a test fails, fix the struct, not
the test.
"""
from __future__ import annotations

import ctypes as ct
import os
import sys
import winreg

# --- Constants (spec v3.15 section 2.1.2) -----------------------------------
SDRPLAY_MAX_DEVICES = 16
MAX_BB_GR = 59  # max baseband gain reduction (dB)

# Device IDs
SDRPLAY_RSP1_ID = 1
SDRPLAY_RSP2_ID = 2
SDRPLAY_RSPDUO_ID = 3
SDRPLAY_RSPDX_ID = 4
SDRPLAY_RSP1B_ID = 6
SDRPLAY_RSPDXR2_ID = 7
SDRPLAY_RSP1A_ID = 255

# TunerSelectT
TUNER_NEITHER, TUNER_A, TUNER_B, TUNER_BOTH = 0, 1, 2, 3

# Bw_MHzT (values are kHz)
BW_0_200, BW_0_300, BW_0_600, BW_1_536 = 200, 300, 600, 1536
BW_5_000, BW_6_000, BW_7_000, BW_8_000 = 5000, 6000, 7000, 8000

# If_kHzT
IF_UNDEFINED, IF_ZERO, IF_0_450, IF_1_620, IF_2_048 = -1, 0, 450, 1620, 2048

# LoModeT
LO_AUTO = 1

# MinGainReductionT
NORMAL_MIN_GR = 20

# AgcControlT
AGC_DISABLE, AGC_100HZ, AGC_50HZ, AGC_5HZ, AGC_CTRL_EN = 0, 1, 2, 3, 4

# TransferModeT
MODE_ISOCH, MODE_BULK = 0, 1

# RspDx antenna select
RSPDX_ANT_A, RSPDX_ANT_B, RSPDX_ANT_C = 0, 1, 2

# ReasonForUpdateT (bitmask)
UPD_NONE = 0x00000000
UPD_DEV_FS = 0x00000001
UPD_TUNER_GR = 0x00008000
UPD_TUNER_FRF = 0x00020000
UPD_TUNER_BWT = 0x00040000
UPD_TUNER_IFT = 0x00080000
UPD_CTRL_DC_IQ = 0x00400000
UPD_CTRL_AGC = 0x01000000
UPD_CTRL_OVERLOAD_ACK = 0x04000000

# ReasonForUpdateExtension1T (bitmask)
EXT1_NONE = 0x00000000
EXT1_RSPDX_HDR_ENABLE = 0x00000001
EXT1_RSPDX_BIAS_T = 0x00000002
EXT1_RSPDX_ANTENNA = 0x00000004
EXT1_RSPDX_RF_NOTCH = 0x00000008
EXT1_RSPDX_RF_DAB_NOTCH = 0x00000010
EXT1_RSPDX_HDR_BW = 0x00000020

# EventT
EVT_GAIN_CHANGE = 0
EVT_POWER_OVERLOAD = 1
EVT_DEVICE_REMOVED = 2
EVT_RSPDUO_MODE = 3
EVT_DEVICE_FAILURE = 4

# PowerOverloadCbEventIdT
OVERLOAD_DETECTED = 0
OVERLOAD_CORRECTED = 1


# --- Structs (field order per spec v3.15 sections 2.1.4-2.10) ----------------
class FsFreqT(ct.Structure):
    _fields_ = [("fsHz", ct.c_double), ("syncUpdate", ct.c_ubyte), ("reCal", ct.c_ubyte)]


class SyncUpdateT(ct.Structure):
    _fields_ = [("sampleNum", ct.c_uint), ("period", ct.c_uint)]


class ResetFlagsT(ct.Structure):
    _fields_ = [("resetGainUpdate", ct.c_ubyte), ("resetRfUpdate", ct.c_ubyte),
                ("resetFsUpdate", ct.c_ubyte)]


class GainValuesT(ct.Structure):
    _fields_ = [("curr", ct.c_float), ("max", ct.c_float), ("min", ct.c_float)]


class GainT(ct.Structure):
    _fields_ = [("gRdB", ct.c_int), ("LNAstate", ct.c_ubyte), ("syncUpdate", ct.c_ubyte),
                ("minGr", ct.c_int), ("gainVals", GainValuesT)]


class RfFreqT(ct.Structure):
    _fields_ = [("rfHz", ct.c_double), ("syncUpdate", ct.c_ubyte)]


class DcOffsetTunerT(ct.Structure):
    _fields_ = [("dcCal", ct.c_ubyte), ("speedUp", ct.c_ubyte),
                ("trackTime", ct.c_int), ("refreshRateTime", ct.c_int)]


class TunerParamsT(ct.Structure):
    _fields_ = [("bwType", ct.c_int), ("ifType", ct.c_int), ("loMode", ct.c_int),
                ("gain", GainT), ("rfFreq", RfFreqT), ("dcOffsetTuner", DcOffsetTunerT)]


class DcOffsetT(ct.Structure):
    _fields_ = [("DCenable", ct.c_ubyte), ("IQenable", ct.c_ubyte)]


class DecimationT(ct.Structure):
    _fields_ = [("enable", ct.c_ubyte), ("decimationFactor", ct.c_ubyte),
                ("wideBandSignal", ct.c_ubyte)]


class AgcT(ct.Structure):
    _fields_ = [("enable", ct.c_int), ("setPoint_dBfs", ct.c_int),
                ("attack_ms", ct.c_ushort), ("decay_ms", ct.c_ushort),
                ("decay_delay_ms", ct.c_ushort), ("decay_threshold_dB", ct.c_ushort),
                ("syncUpdate", ct.c_int)]


class ControlParamsT(ct.Structure):
    _fields_ = [("dcOffset", DcOffsetT), ("decimation", DecimationT),
                ("agc", AgcT), ("adsbMode", ct.c_int)]


class Rsp1aParamsT(ct.Structure):
    _fields_ = [("rfNotchEnable", ct.c_ubyte), ("rfDabNotchEnable", ct.c_ubyte)]


class Rsp1aTunerParamsT(ct.Structure):
    _fields_ = [("biasTEnable", ct.c_ubyte)]


class Rsp2ParamsT(ct.Structure):
    _fields_ = [("extRefOutputEn", ct.c_ubyte)]


class Rsp2TunerParamsT(ct.Structure):
    _fields_ = [("biasTEnable", ct.c_ubyte), ("amPortSel", ct.c_int),
                ("antennaSel", ct.c_int), ("rfNotchEnable", ct.c_ubyte)]


class RspDuo_ResetSlaveFlagsT(ct.Structure):
    _fields_ = [("resetGainUpdate", ct.c_ubyte), ("resetRfUpdate", ct.c_ubyte)]


class RspDuoTunerParamsT(ct.Structure):
    _fields_ = [("biasTEnable", ct.c_ubyte), ("tuner1AmPortSel", ct.c_int),
                ("tuner1AmNotchEnable", ct.c_ubyte), ("rfNotchEnable", ct.c_ubyte),
                ("rfDabNotchEnable", ct.c_ubyte), ("resetSlaveFlags", RspDuo_ResetSlaveFlagsT)]


class RspDuoParamsT(ct.Structure):
    _fields_ = [("extRefOutputEn", ct.c_int)]


class RspDxParamsT(ct.Structure):
    _fields_ = [("hdrEnable", ct.c_ubyte), ("biasTEnable", ct.c_ubyte),
                ("antennaSel", ct.c_int), ("rfNotchEnable", ct.c_ubyte),
                ("rfDabNotchEnable", ct.c_ubyte)]


class RspDxTunerParamsT(ct.Structure):
    _fields_ = [("hdrBw", ct.c_int)]


class RxChannelParamsT(ct.Structure):
    _fields_ = [("tunerParams", TunerParamsT), ("ctrlParams", ControlParamsT),
                ("rsp1aTunerParams", Rsp1aTunerParamsT), ("rsp2TunerParams", Rsp2TunerParamsT),
                ("rspDuoTunerParams", RspDuoTunerParamsT), ("rspDxTunerParams", RspDxTunerParamsT)]


class DevParamsT(ct.Structure):
    _fields_ = [("ppm", ct.c_double), ("fsFreq", FsFreqT), ("syncUpdate", SyncUpdateT),
                ("resetFlags", ResetFlagsT), ("mode", ct.c_int), ("samplesPerPkt", ct.c_uint),
                ("rsp1aParams", Rsp1aParamsT), ("rsp2Params", Rsp2ParamsT),
                ("rspDuoParams", RspDuoParamsT), ("rspDxParams", RspDxParamsT)]


class DeviceParamsT(ct.Structure):
    _fields_ = [("devParams", ct.POINTER(DevParamsT)),
                ("rxChannelA", ct.POINTER(RxChannelParamsT)),
                ("rxChannelB", ct.POINTER(RxChannelParamsT))]


class DeviceT(ct.Structure):
    _fields_ = [("SerNo", ct.c_char * 64), ("hwVer", ct.c_ubyte), ("tuner", ct.c_int),
                ("rspDuoMode", ct.c_int), ("valid", ct.c_ubyte),
                ("rspDuoSampleFreq", ct.c_double), ("dev", ct.c_void_p)]


class StreamCbParamsT(ct.Structure):
    _fields_ = [("firstSampleNum", ct.c_uint), ("grChanged", ct.c_int),
                ("rfChanged", ct.c_int), ("fsChanged", ct.c_int), ("numSamples", ct.c_uint)]


class GainCbParamT(ct.Structure):
    _fields_ = [("gRdB", ct.c_uint), ("lnaGRdB", ct.c_uint), ("currGain", ct.c_double)]


class PowerOverloadCbParamT(ct.Structure):
    _fields_ = [("powerOverloadChangeType", ct.c_int)]


class RspDuoModeCbParamT(ct.Structure):
    _fields_ = [("modeChangeType", ct.c_int)]


class EventParamsT(ct.Union):
    _fields_ = [("gainParams", GainCbParamT), ("powerOverloadParams", PowerOverloadCbParamT),
                ("rspDuoModeParams", RspDuoModeCbParamT)]


# --- Callback prototypes (v3 signatures) -------------------------------------
StreamCallbackT = ct.CFUNCTYPE(None, ct.POINTER(ct.c_short), ct.POINTER(ct.c_short),
                               ct.POINTER(StreamCbParamsT), ct.c_uint, ct.c_uint, ct.c_void_p)
EventCallbackT = ct.CFUNCTYPE(None, ct.c_int, ct.c_int, ct.POINTER(EventParamsT), ct.c_void_p)


class CallbackFnsT(ct.Structure):
    _fields_ = [("StreamACbFn", StreamCallbackT), ("StreamBCbFn", StreamCallbackT),
                ("EventCbFn", EventCallbackT)]


# --- DLL discovery + function layer -------------------------------------------
class SdrplayError(RuntimeError):
    def __init__(self, err: int, where: str):
        super().__init__(f"SDRplay API error {err} in {where}")


def find_dll(dll_path: str | None = None) -> str:
    """Locate sdrplay_api.dll: explicit path > registry Install_Dir > Program Files."""
    if dll_path:
        if os.path.exists(dll_path):
            return dll_path
        raise FileNotFoundError(f"explicit DLL path does not exist: {dll_path}")
    if sys.platform == "win32":
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                r"SOFTWARE\SDRplay\Service\API") as k:
                install_dir, _ = winreg.QueryValueEx(k, "Install_Dir")
            candidate = os.path.join(install_dir, "x64", "sdrplay_api.dll")
            if os.path.exists(candidate):
                return candidate
        except OSError:
            pass
    fallback = r"C:\Program Files\SDRplay\x64\sdrplay_api.dll"
    if os.path.exists(fallback):
        return fallback
    raise FileNotFoundError(
        "sdrplay_api.dll not found - install SDRplay API v3 (>= 3.15)")


class SdrplayApi:
    """Owns the DLL handle and the Open/Close lifecycle."""

    def __init__(self, dll_path: str | None = None):
        self.lib = ct.CDLL(find_dll(dll_path))
        self._setup_prototypes()
        self._check(self.lib.sdrplay_api_Open(), "sdrplay_api_Open")

    def _setup_prototypes(self) -> None:
        L = self.lib
        L.sdrplay_api_Close.restype = ct.c_int
        L.sdrplay_api_Close.argtypes = []
        L.sdrplay_api_ApiVersion.restype = ct.c_int
        L.sdrplay_api_ApiVersion.argtypes = [ct.POINTER(ct.c_float)]
        L.sdrplay_api_LockDeviceApi.restype = ct.c_int
        L.sdrplay_api_LockDeviceApi.argtypes = []
        L.sdrplay_api_UnlockDeviceApi.restype = ct.c_int
        L.sdrplay_api_UnlockDeviceApi.argtypes = []
        L.sdrplay_api_GetDevices.restype = ct.c_int
        L.sdrplay_api_GetDevices.argtypes = [ct.POINTER(DeviceT), ct.POINTER(ct.c_uint), ct.c_uint]
        L.sdrplay_api_SelectDevice.restype = ct.c_int
        L.sdrplay_api_SelectDevice.argtypes = [ct.POINTER(DeviceT)]
        L.sdrplay_api_ReleaseDevice.restype = ct.c_int
        L.sdrplay_api_ReleaseDevice.argtypes = [ct.POINTER(DeviceT)]
        L.sdrplay_api_GetErrorString.restype = ct.c_char_p
        L.sdrplay_api_GetErrorString.argtypes = [ct.c_int]
        L.sdrplay_api_GetDeviceParams.restype = ct.c_int
        L.sdrplay_api_GetDeviceParams.argtypes = [ct.c_void_p, ct.POINTER(ct.POINTER(DeviceParamsT))]
        L.sdrplay_api_Init.restype = ct.c_int
        L.sdrplay_api_Init.argtypes = [ct.c_void_p, ct.POINTER(CallbackFnsT), ct.c_void_p]
        L.sdrplay_api_Uninit.restype = ct.c_int
        L.sdrplay_api_Uninit.argtypes = [ct.c_void_p]
        L.sdrplay_api_Update.restype = ct.c_int
        L.sdrplay_api_Update.argtypes = [ct.c_void_p, ct.c_int, ct.c_int, ct.c_int]

    # -- helpers -----------------------------------------------------------------
    def _check(self, err: int, where: str) -> None:
        if err:
            msg = self.lib.sdrplay_api_GetErrorString(err)
            raise SdrplayError(
                err, f"{where} ({msg.decode(errors='replace') if msg else '?'})")

    def error_string(self, err: int) -> str:
        msg = self.lib.sdrplay_api_GetErrorString(err)
        return msg.decode(errors="replace") if msg else str(err)

    @property
    def version(self) -> float:
        v = ct.c_float()
        self._check(self.lib.sdrplay_api_ApiVersion(ct.byref(v)), "sdrplay_api_ApiVersion")
        return v.value

    # -- device enumeration / selection --------------------------------------------
    def _get_locked_devices(self) -> list[DeviceT]:
        devs = (DeviceT * SDRPLAY_MAX_DEVICES)()
        n = ct.c_uint(0)
        self._check(self.lib.sdrplay_api_GetDevices(devs, ct.byref(n), SDRPLAY_MAX_DEVICES),
                    "sdrplay_api_GetDevices")
        return [devs[i] for i in range(n.value) if devs[i].valid]

    def list_devices(self) -> list[DeviceT]:
        self._check(self.lib.sdrplay_api_LockDeviceApi(), "sdrplay_api_LockDeviceApi")
        try:
            return self._get_locked_devices()
        finally:
            self._check(self.lib.sdrplay_api_UnlockDeviceApi(), "sdrplay_api_UnlockDeviceApi")

    def select(self, device_id: int = SDRPLAY_RSPDX_ID) -> DeviceT:
        """Lock -> enumerate -> select matching hwVer -> unlock (official example flow)."""
        self._check(self.lib.sdrplay_api_LockDeviceApi(), "sdrplay_api_LockDeviceApi")
        try:
            devs = self._get_locked_devices()
            chosen = next((d for d in devs if d.hwVer == device_id), None)
            if chosen is None:
                raise SdrplayError(
                    1, f"select: no device with hwVer={device_id} "
                       f"(found hwVers {[d.hwVer for d in devs]})")
            self._check(self.lib.sdrplay_api_SelectDevice(ct.byref(chosen)),
                        "sdrplay_api_SelectDevice")
            return chosen
        finally:
            self._check(self.lib.sdrplay_api_UnlockDeviceApi(), "sdrplay_api_UnlockDeviceApi")

    def close(self) -> None:
        self._check(self.lib.sdrplay_api_Close(), "sdrplay_api_Close")
