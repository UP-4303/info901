from __future__ import annotations

class LamportClock:
    def __init__(self):
        self.clock = 0

    def tick(self):
        self.clock += 1

    def sync(self, other: int):
        self.clock = max(self.clock, other)+1