from threading import Thread, Event
from time import sleep

class LoopTask(Thread):
    def __init__(self, repeatEvery: float | int, callback, parameters, killEvent: Event):
        super(LoopTask, self).__init__()
        self.repeatEvery = repeatEvery
        self.callback = callback
        self.parameters = parameters
        self.killEvent = killEvent
        self.start()

    def run(self):
        while not self.killEvent.is_set():
            self.callback(*self.parameters)
            self.killEvent.wait(self.repeatEvery)