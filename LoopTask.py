from threading import Thread, Event
from time import sleep

class LoopTask(Thread):
    def __init__(self, repeatEvery: float | int, callback, parameters, keepAliveEvent: Event):
        super(LoopTask, self).__init__()
        self.repeatEvery = repeatEvery
        self.callback = callback
        self.parameters = parameters
        self.keepAliveEvent = keepAliveEvent
        self.start()

    def run(self):
        while self.keepAliveEvent.is_set():
            self.callback(*self.parameters)
            sleep(self.repeatEvery)