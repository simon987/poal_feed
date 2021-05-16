from hexlib.db import VolatileBooleanState


class PoalState:
    def __init__(self, prefix):
        self._state = VolatileBooleanState(prefix, sep=".")

    def mark_visited(self, pid):
        self._state["pid"][pid] = True

    def has_visited(self, pid):
        return self._state["pid"][pid]
