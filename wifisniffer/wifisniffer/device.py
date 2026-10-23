"""RSPdx session: API lifecycle + IQ queue feeding the sniffer pipeline.

IQ arrives as int16 I/Q on an API-owned thread; the stream callback must stay
fast (one numpy copy per block) and the bounded queue drops the oldest block
under sustained overload.
"""
from __future__ import annotations

import ctypes as ct
import queue

import numpy as np

from . import api
from .api import (
    AGC_DISABLE, BW_6_000, EVT_DEVICE_REMOVED, EVT_GAIN_CHANGE, EVT_POWER_OVERLOAD,
    EXT1_NONE, IF_ZERO, SDRPLAY_RSPDX_ID, TUNER_A, UPD_CTRL_OVERLOAD_ACK, UPD_TUNER_FRF,
    SdrplayApi, SdrplayError,
)


class SdrplaySession:
    def __init__(self, fs_hz: float = 6_048_000.0, bw: int = BW_6_000, lna_state: int = 8,
                 gr_db: int = 40, antenna: int = api.RSPDX_ANT_A,
                 device_id: int = SDRPLAY_RSPDX_ID, max_blocks: int = 96,
                 initial_freq_hz: float = 865.8e6):
        self.fs_hz = fs_hz
        self.bw = bw
        self.lna_state = lna_state
        self.gr_db = gr_db
        self.antenna = antenna
        self.device_id = device_id
        self.initial_freq_hz = initial_freq_hz
        self._q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=max_blocks)
        self._api = SdrplayApi()
        self._dev: api.DeviceT | None = None
        self._params: ct.POINTER(api.DeviceParamsT) | None = None
        self._keepalive: list = []
        self.last_gain_db: float | None = None
        self.overload_events = 0
        self.device_removed = False

    # -- lifecycle ---------------------------------------------------------------
    def __enter__(self) -> "SdrplaySession":
        self._dev = self._api.select(self.device_id)
        dp = ct.POINTER(api.DeviceParamsT)()
        self._api._check(
            self._api.lib.sdrplay_api_GetDeviceParams(self._dev.dev, ct.byref(dp)),
            "sdrplay_api_GetDeviceParams")
        if not dp:
            raise SdrplayError(1, "GetDeviceParams returned NULL")
        self._params = dp  # keep the reference alive for the session

        devp = dp.contents.devParams.contents
        rx = dp.contents.rxChannelA.contents
        devp.fsFreq.fsHz = self.fs_hz
        rx.tunerParams.rfFreq.rfHz = self.initial_freq_hz
        rx.tunerParams.bwType = self.bw
        rx.tunerParams.ifType = IF_ZERO
        rx.tunerParams.gain.gRdB = self.gr_db
        rx.tunerParams.gain.LNAstate = self.lna_state
        rx.ctrlParams.agc.enable = AGC_DISABLE
        rx.ctrlParams.dcOffset.DCenable = 1
        rx.ctrlParams.dcOffset.IQenable = 1
        devp.rspDxParams.antennaSel = self.antenna
        devp.rspDxParams.biasTEnable = 0

        stream_cb = api.StreamCallbackT(self._on_stream)
        event_cb = api.EventCallbackT(self._on_event)
        cbs = api.CallbackFnsT(stream_cb, stream_cb, event_cb)
        self._keepalive += [stream_cb, event_cb, cbs]
        self._api._check(self._api.lib.sdrplay_api_Init(self._dev.dev, ct.byref(cbs), None),
                         "sdrplay_api_Init")
        return self

    def __exit__(self, *exc) -> None:
        assert self._dev is not None
        errs = []
        try:
            errs.append(self._api.lib.sdrplay_api_Uninit(self._dev.dev))
        except Exception as e:  # noqa: BLE001 - teardown must continue
            errs.append(str(e))
        try:
            errs.append(self._api.lib.sdrplay_api_ReleaseDevice(ct.byref(self._dev)))
        except Exception as e:  # noqa: BLE001
            errs.append(str(e))
        try:
            self._api.close()
        except Exception as e:  # noqa: BLE001
            errs.append(str(e))
        bad = [e for e in errs if e]
        if bad:
            print(f"WARNING: non-clean teardown: {bad}", flush=True)

    # -- control -------------------------------------------------------------------
    def tune(self, freq_hz: float) -> None:
        """Write freq into the param struct, then apply via Update (spec section 3.17)."""
        self._params.contents.rxChannelA.contents.tunerParams.rfFreq.rfHz = float(freq_hz)
        self._api._check(
            self._api.lib.sdrplay_api_Update(self._dev.dev, TUNER_A, UPD_TUNER_FRF, EXT1_NONE),
            "sdrplay_api_Update(Frf)")

    def read(self, timeout_s: float = 0.05) -> np.ndarray | None:
        """Next IQ block (complex64, int16 values) or None on timeout."""
        try:
            return self._q.get(timeout=timeout_s)
        except queue.Empty:
            return None

    # -- callbacks (API thread - keep fast) -------------------------------------------
    def _push_block(self, block: np.ndarray) -> None:
        try:
            self._q.put_nowait(block)
        except queue.Full:
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            try:
                self._q.put_nowait(block)
            except queue.Full:
                pass  # drop; the sniffer tolerates gaps

    def _on_stream(self, xi, xq, params, num_samples, reset, ctx) -> None:
        n = int(num_samples)
        if n == 0 or reset:
            return
        i = np.ctypeslib.as_array(xi, shape=(n,))
        q = np.ctypeslib.as_array(xq, shape=(n,))
        block = (i.astype(np.int32) + 1j * q.astype(np.int32)).astype(np.complex64)
        self._push_block(block)

    def _on_event(self, event_id, tuner, params, ctx) -> None:
        if event_id == EVT_GAIN_CHANGE:
            self.last_gain_db = float(params.contents.gainParams.currGain)
        elif event_id == EVT_POWER_OVERLOAD:
            self.overload_events += 1
            # ACK required (official example does this from within the callback)
            try:
                self._api.lib.sdrplay_api_Update(self._dev.dev, tuner,
                                                 UPD_CTRL_OVERLOAD_ACK, EXT1_NONE)
            except Exception:  # noqa: BLE001
                pass
        elif event_id == EVT_DEVICE_REMOVED:
            self.device_removed = True
