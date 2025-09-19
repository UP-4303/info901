from __future__ import annotations
import collections
from time import sleep
from pyeventbus3.pyeventbus3 import *

from threading import Lock, Event

from random import randint

from Mailbox import Mailbox
from Message import Message, AutoIdMessage, AckMessage, SyncMessage, TokenMessage, JoinMessage, HeartbitMessage
from LamportClock import LamportClock
from LoopTask import LoopTask

class Com:
    timeout = 1
    maxRand = 100

    def __init__(self, name: str):
        self.mailbox = Mailbox()
        self.clock = LamportClock()
        PyBus.Instance().register(self, self)

        self.name = name
        self.nameTable = dict[str, int]()
        self.heartbitMutex = Lock()
        self.heartbitTable = dict[int, float]()

        self.receivedNumbers: list[tuple[int, str]] = []
        self.mutex = Lock()
        self.id: None | int = None
        self.nbProcess: None | int = None

        self.ackEvent: Event = Event()
        self.waitingForAck: int = 0
        self.waitingForAckLock: Lock = Lock()

        self.syncEvent: Event = Event()
        self.receiveLock: Lock = Lock()
        self.syncMessage: SyncMessage | None = None

        self.requestTokenEvent: Event = Event()
        self.releaseTokenEvent: Event = Event()
        self.releaseTokenEvent.set()
        self.waitingForToken: bool = False

        self.joinEvent: Event = Event()
        self.joiningIds: set = set()

        self.alive: Event = Event()
        self.initializedEvent: Event = Event()

        self.autoId()
        self.startToken()
        self.initializedEvent.set()

        LoopTask(1, self.sendHeartbit, (), self.alive)
        LoopTask(5, self.checkHearbits, (), self.alive)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=AutoIdMessage)
    def onAutoIdReceive(self, message: AutoIdMessage):
        with self.mutex:
            self.receivedNumbers.append(message.content)

    def autoId(self) -> None:
        self.alive.set()

        myNumber = None
        sleep(Com.timeout)
        while True:
            if myNumber == None:
                myNumber = randint(0, Com.maxRand)
                PyBus.Instance().post(AutoIdMessage([myNumber, self.name]))
            sleep(Com.timeout)
            
            with self.mutex:
                numbers = [item[0] for item in self.receivedNumbers]
            duplicate = [num for num, count in collections.Counter(numbers).items() if count > 1]
            if len(duplicate) > 0:
                with self.mutex:
                    self.receivedNumbers = [item for item in self.receivedNumbers if not item[0] in duplicate]
                if myNumber in duplicate:
                    myNumber = None
            else:
                break

        with self.mutex:
            self.receivedNumbers.sort()
            for i, item in enumerate(self.receivedNumbers):
                self.nameTable[item[1]] = i
                if item[0] == myNumber and item[1] == self.name:
                    self.id = i

            print(f"<{self.name}:{self.id}> nameTable: {self.nameTable}", flush=True)
            self.nbProcess = len(self.receivedNumbers)
    
    def startToken(self) -> None:
        if self.id == self.nbProcess - 1:
            sleep(Com.timeout)
            PyBus.Instance().post(TokenMessage(self.id, 0))

    def getNbProcess(self) -> int:
        return self.nbProcess

    def sendTo(self, message: any, dest: str):
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> sending "{message}" to <{dest}:{self.nameTable[dest]}> with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, self.nameTable[dest], message, self.clock.clock))

    def sendToSync(self, message: any, dest: str):
        with self.waitingForAckLock:
            self.waitingForAck = 1
        PyBus.Instance().post(SyncMessage(self.id, self.nameTable[dest], message, self.clock.clock))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def recevFromSync(self, src: str) -> Message:
        self.syncEvent.wait()
        self.syncEvent.clear()
        PyBus.Instance().post(AckMessage(self.id, self.nameTable[src]))
        msg = self.syncMessage
        self.clock.sync(msg.clock)
        self.syncMessage = None
        self.receiveLock.release()
        return msg
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent=AckMessage)
    def onAckReceive(self, message: AckMessage):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()
        if message.recipient != self.id:
            return
        
        with self.waitingForAckLock:
            self.waitingForAck -= 1
            if self.waitingForAck == 0:
                self.ackEvent.set()
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent=SyncMessage)
    def onSyncReceive(self, message: SyncMessage):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()
        if message.recipient != self.id:
            return
        
        self.syncEvent.set()
        self.receiveLock.acquire()
        self.syncMessage = message

    def synchronize(self):
        print(f"<{self.name}:{self.id}> is synchronizing", flush=True)
        PyBus.Instance().post(JoinMessage(self.id))
        self.joinEvent.wait()
        self.joinEvent.clear()
        self.joiningIds.clear()
        print(f"<{self.name}:{self.id}> synchronized with {self.nbProcess - 1} others", flush=True)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=JoinMessage)
    def onJoinRecieve(self, message: JoinMessage):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        self.joiningIds.add(message.sender)
        print(f"<{self.name}:{self.id}> received join from {message.sender}, currently at {len(self.joiningIds)}/{self.nbProcess}", flush=True)
        if len(self.joiningIds) == self.nbProcess:
            self.joinEvent.set()

    def requestSC(self):
        print(f"<{self.name}:{self.id}> is requesting critical section", flush=True)
        self.waitingForToken = True
        self.releaseTokenEvent.clear()
        self.requestTokenEvent.wait()
        self.requestTokenEvent.clear()
        print(f"<{self.name}:{self.id}> got the token", flush=True)

    def releaseSC(self):
        print(f"<{self.name}:{self.id}> is releasing critical section", flush=True)
        self.releaseTokenEvent.set()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=TokenMessage)
    def onTokenReceive(self, message: TokenMessage):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()
        if message.recipient != self.id:
            return
        
        if self.waitingForToken:
            self.waitingForToken = False
            self.requestTokenEvent.set()
        self.releaseTokenEvent.wait()
        PyBus.Instance().post(TokenMessage(self.id, (self.id + 1) % self.nbProcess))

    def sendHeartbit(self):
        PyBus.Instance().post(HeartbitMessage(self.id))
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent= HeartbitMessage)
    def receiveHeartbit(self, message: HeartbitMessage):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        with self.heartbitMutex:
            self.heartbitTable[message.sender] = time.time()

    def broadcast(self, message: any):
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> broadcasting "{message}" with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock))
    
    def ackNeededBroadcast(self, message: any):
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> broadcasting "{message}" asking for ACK with clock {self.clock.clock}', flush=True)
        with self.waitingForAckLock:
            self.waitingForAck = self.nbProcess
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock, ackNeeded=True))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def checkHearbits(self):
        with self.heartbitMutex

    @subscribe(threadMode= Mode.PARALLEL, onEvent=Message)
    def onReceive(self, message: Message):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()
        if message.recipient != self.id and message.recipient is not None:
            return
        if message.isSystem:
            return
        
        self.clock.sync(message.clock)
        print(f'<{self.name}:{self.id}> receiving "{message.content}" from {message.sender} with clock {self.clock.clock}', flush=True)
        self.mailbox.addMessage(message)
        if message.ackNeeded:
            print(f'<{self.name}:{self.id}> sending ACK to {message.sender}', flush=True)
            PyBus.Instance().post(AckMessage(self.id, message.sender))