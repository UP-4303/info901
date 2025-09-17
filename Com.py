import collections
from time import sleep
from pyeventbus3.pyeventbus3 import *

from threading import Lock, Event

from random import randint

from Mailbox import Mailbox
from Message import Message, AutoIdMessage, AckMessage, SyncMessage

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

        self.ackEvent: Event = Event()
        self.syncEvent: Event = Event()
        self.syncMessage: SyncMessage | None = None

        self.autoId()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=AutoIdMessage)
    def onAutoIdReceive(self, message: AutoIdMessage):
        with self.mutex:
            self.receivedNumbers.append(message.content)

    def autoId(self) -> None:
        sleep(Com.timeout)
        myNumber = None
        while True:
            if myNumber == None:
                myNumber = randint(0, Com.maxRand)
                PyBus.Instance().post(AutoIdMessage(None, None, myNumber))
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
        PyBus.Instance().post(Message(self.id, destId, message))

    def sendToSync(self, message: any, destId: int):
        PyBus.Instance().post(SyncMessage(self.id, destId, message))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def recevFromSync(self, srcId: int) -> Message:
        self.syncEvent.wait()
        self.syncEvent.clear()
        PyBus.Instance().post(AckMessage(self.id, srcId))
        msg = self.syncMessage
        self.syncMessage = None
        return msg
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent=AckMessage)
    def onAutoIdReceive(self, message: AckMessage):
        if message.recipient == self.id:
            self.ackEvent.set()
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent=SyncMessage)
    def onAutoIdReceive(self, message: SyncMessage):
        if message.recipient == self.id:
            self.syncEvent.set()
            self.syncMessage = message

    def synchronize(self):
        pass

    def requestSC(self):
        pass

    def releaseSC(self):
        pass

    def broadcast(self, message: any):
        PyBus.Instance().post(Message(self.id, None, message))

    @subscribe(threadMode= Mode.PARALLEL, onEvent=Message)
    def onReceive(self, message: Message):
        if message.recipient != self.id or message.isSystem:
            return
        self.mailbox.addMessage(message)
