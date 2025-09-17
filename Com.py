import collections
from time import sleep
from pyeventbus3.pyeventbus3 import *

from threading import Lock

from random import randint

from Mailbox import Mailbox
from Message import Message, AutoIdMessage

class Com:
    timeout = 1
    maxRand = 100

    def __init__(self):
        self.mailbox = Mailbox()
        PyBus.Instance().register(self, self)

        self.receivedNumbers = []
        self.mutex = Lock()
        self.id: None | int = None
        self.nbProcess: None | int = None
        self.autoId()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=AutoIdMessage)
    def onAutoIdReceive(self, message: AutoIdMessage):
        with self.mutex:
            self.receivedNumbers.append(message.content)
            print(self.receivedNumbers)

    def autoId(self) -> None:
        sleep(Com.timeout)
        myNumber = None
        while True:
            if myNumber == None:
                myNumber = randint(0, Com.maxRand)
                print(myNumber)
                self.broadcast(AutoIdMessage(None, None, myNumber))
            sleep(Com.timeout)
            
            duplicate = [item for item, count in collections.Counter(self.receivedNumbers).items() if count > 1]
            if len(duplicate) > 0:
                self.receivedNumbers = [item for item in self.receivedNumbers if not item in duplicate]
                if myNumber in duplicate:
                    myNumber = None
            else:
                break

        self.receivedNumbers.sort()
        self.id = self.receivedNumbers.index(myNumber)
        self.nbProcess = len(self.receivedNumbers)
        return
    
    def getNbProcess(self) -> int:
        return self.nbProcess

    def getMyId(self) -> int:
        return self.id

    def sendTo(self, message: any, destId: int):
        pass

    def sendToSync(self, message: any, destId: int):
        pass

    def recevFromSync(self, srcId: int) -> Message:
        pass

    def synchronize(self):
        pass

    def requestSC(self):
        pass

    def releaseSC(self):
        pass

    def broadcast(self, message: any):
        PyBus.Instance().post(message)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=Message)
    def onReceive(self, message: Message):
        if message.recipient != self.myId or message.isSystem:
            return
        self.mailbox.addMessage(message)
