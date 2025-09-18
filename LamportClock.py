from threading import Lock

class LamportClock:

    def __init__(self):
        self.semaphore = Lock()
        self.clock = 0

    def inc_clock(self):
        with self.semaphore:
            self.clock += 1

    def sync(self, other: int):
        with self.semaphore:
            self.clock = max(self.clock, other)+1