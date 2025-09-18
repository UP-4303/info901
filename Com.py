import collections
from time import sleep
from pyeventbus3.pyeventbus3 import *

from threading import Lock, Event

from random import randint

from Mailbox import Mailbox
from Message import Message, AutoIdMessage, AckMessage, SyncMessage, TokenMessage, JoinMessage
from LamportClock import LamportClock

class Com:
    timeout = 1
    maxRand = 100

    def __init__(self):
        self.mailbox = Mailbox()
        self.clock = LamportClock()
        PyBus.Instance().register(self, self)

        self.receivedNumbers = []
        self.mutex = Lock()
        self.id: None | int = None
        self.nbProcess: None | int = None

        self.ackEvent: Event = Event()
        self.syncEvent: Event = Event()
        self.syncMessage: SyncMessage | None = None

        self.tokenEvent: Event = Event()
        self.waitingForToken: bool = False

        self.joinEvent: Event = Event()
        self.joiningIds: set = set()

        self.alive = False

        self.autoId()
        self.startToken()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=AutoIdMessage)
    def onAutoIdReceive(self, message: AutoIdMessage):
        with self.mutex:
            self.receivedNumbers.append(message.content)

    def autoId(self) -> None:
        self.alive = True

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
    
    def startToken(self) -> None:
        if self.id == self.nbProcess - 1:
            sleep(Com.timeout)
            PyBus.Instance().post(TokenMessage(self.id, 0))

    def getNbProcess(self) -> int:
        return self.nbProcess

    def getMyId(self) -> int:
        return self.id

    def sendTo(self, message: any, destId: int):
        self.clock.inc_clock()
        print(f'{self.id} sending "{message}" to {destId} with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, destId, message, self.clock.clock))

    def sendToSync(self, message: any, destId: int):
        PyBus.Instance().post(SyncMessage(self.id, destId, message, self.clock.clock))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def recevFromSync(self, srcId: int) -> Message:
        self.syncEvent.wait()
        self.syncEvent.clear()
        PyBus.Instance().post(AckMessage(self.id, srcId))
        msg = self.syncMessage
        self.clock.sync(msg.clock)
        self.syncMessage = None
        return msg
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent=AckMessage)
    def onAckReceive(self, message: AckMessage):
        if message.recipient == self.id and self.alive:
            self.ackEvent.set()
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent=SyncMessage)
    def onSyncReceive(self, message: SyncMessage):
        if message.recipient == self.id and self.alive:
            self.syncEvent.set()
            self.syncMessage = message

    def synchronize(self):
        print("Process "+str(self.id)+" is synchronizing", flush=True)
        PyBus.Instance().post(JoinMessage(self.id))
        self.joinEvent.wait()
        self.joinEvent.clear()
        self.joiningIds.clear()
        print("Process "+str(self.id)+" synchronized with "+str(self.nbProcess - 1)+" others", flush=True)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=JoinMessage)
    def onJoinRecieve(self, message: JoinMessage):
        if not self.alive:
            return
        print("Process "+str(self.id)+" received join from "+str(message.sender), flush=True)
        self.joiningIds.add(message.sender)
        print("Process "+str(self.id)+" currently joined with "+str(len(self.joiningIds))+"/"+str(self.nbProcess), flush=True)
        if len(self.joiningIds) == self.nbProcess:
            self.joinEvent.set()

    def requestSC(self):
        print("Process "+str(self.id)+" is requesting critical section", flush=True)
        self.waitingForToken = True
        self.tokenEvent.wait()
        self.tokenEvent.clear()
        print("Process "+str(self.id)+" got the token", flush=True)

    def releaseSC(self):
        print("Process "+str(self.id)+" is releasing critical section", flush=True)
        PyBus.Instance().post(TokenMessage(self.id, (self.id + 1) % self.nbProcess))

    @subscribe(threadMode= Mode.PARALLEL, onEvent=TokenMessage)
    def onTokenReceive(self, message: TokenMessage):
        if message.recipient == self.id and self.alive:
            if self.waitingForToken:
                self.waitingForToken = False
                self.tokenEvent.set()
            else:
                PyBus.Instance().post(TokenMessage(self.id, (self.id + 1) % self.nbProcess))

    def broadcast(self, message: any):
        self.clock.inc_clock()
        print(f'{self.id} broadcasting "{message}" with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock))

    @subscribe(threadMode= Mode.PARALLEL, onEvent=Message)
    def onReceive(self, message: Message):
        if message.recipient != self.id or message.isSystem or not self.alive:
            return
        self.clock.sync(message.clock)
        print(f'{self.id} receiving "{message.content}" from {message.sender} with clock {self.clock.clock}', flush=True)
        self.mailbox.addMessage(message)
