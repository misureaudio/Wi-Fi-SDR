import queue

import numpy as np

import wifisniffer.device as device_mod


def _bare_session():
    """A session without __init__ (no DLL touched)."""
    return device_mod.SdrplaySession.__new__(device_mod.SdrplaySession)


def test_push_block_drops_oldest_on_overflow():
    s = _bare_session()
    s._q = queue.Queue(maxsize=2)
    for k in range(3):
        s._push_block(np.full(4, k, dtype=np.complex64))
    assert s._q.queue[0][0] == 1.0  # oldest (0) dropped
    assert s._q.qsize() == 2


def test_on_stream_noop_on_empty_or_reset():
    s = _bare_session()
    s._q = queue.Queue(maxsize=2)
    s._on_stream(None, None, None, 0, 0, None)  # num_samples == 0
    s._on_stream(None, None, None, 4, 1, None)  # reset flag set
    assert s._q.empty()
