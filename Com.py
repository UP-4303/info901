from __future__ import annotations
import collections
from time import sleep
from pyeventbus3.pyeventbus3 import *

from threading import Lock, Event

from random import randint

from Mailbox import Mailbox
from Message import Message, AutoIdMessage, AckMessage, SyncMessage, TokenMessage, JoinMessage, HeartbitMessage, ReorgMessage
from LamportClock import LamportClock
from LoopTask import LoopTask

class Com:
    timeout = 1
    maxRand = 100
    sendHeartbitEvery = 1
    checkHeartbitEvery = 5

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
        self.reorgEvent: Event = Event()
        self.reorgEvent.set()

        self.autoId()
        self.startToken()
        self.initializedEvent.set()

        self.killEvent = Event()
        LoopTask(Com.sendHeartbitEvery, self.sendHeartbit, (), self.killEvent)
        LoopTask(Com.checkHeartbitEvery, self.checkHearbits, (), self.killEvent)
    
    def stop(self):
        self.alive.clear()
        self.killEvent.set()

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
        self.reorgEvent.wait()
        if dest not in self.nameTable:
            print(f"<{self.name}:{self.id}> ERROR: destination {dest} unknown", flush=True)
            return

        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> sending "{message}" to <{dest}:{self.nameTable[dest]}> with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, self.nameTable[dest], message, self.clock.clock))

    def sendToSync(self, message: any, dest: str):
        self.reorgEvent.wait()
        if dest not in self.nameTable:
            print(f"<{self.name}:{self.id}> ERROR: destination {dest} unknown", flush=True)
            return

        with self.waitingForAckLock:
            self.waitingForAck = 1
        PyBus.Instance().post(SyncMessage(self.id, self.nameTable[dest], message, self.clock.clock))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def recevFromSync(self, src: str) -> Message:
        self.reorgEvent.wait()
        if src not in self.nameTable:
            print(f"<{self.name}:{self.id}> ERROR: source {src} unknown", flush=True)
            return None

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
        self.reorgEvent.wait()
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
        self.reorgEvent.wait()
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()
        if message.recipient != self.id:
            return
        
        self.syncEvent.set()
        self.receiveLock.acquire()
        self.syncMessage = message

    def synchronize(self):
        self.reorgEvent.wait()
        print(f"<{self.name}:{self.id}> is synchronizing", flush=True)
        PyBus.Instance().post(JoinMessage(self.id))
        self.joinEvent.wait()
        self.joinEvent.clear()
        self.joiningIds.clear()
        print(f"<{self.name}:{self.id}> synchronized with {self.nbProcess - 1} others", flush=True)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=JoinMessage)
    def onJoinRecieve(self, message: JoinMessage):
        self.reorgEvent.wait()
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        self.joiningIds.add(message.sender)
        print(f"<{self.name}:{self.id}> received join from {message.sender}, currently at {len(self.joiningIds)}/{self.nbProcess}", flush=True)
        if len(self.joiningIds) == self.nbProcess:
            self.joinEvent.set()

    def requestSC(self):
        self.reorgEvent.wait()
        print(f"<{self.name}:{self.id}> is requesting critical section", flush=True)
        self.waitingForToken = True
        self.releaseTokenEvent.clear()
        self.requestTokenEvent.wait()
        self.requestTokenEvent.clear()
        print(f"<{self.name}:{self.id}> got the token", flush=True)

    def releaseSC(self):
        self.reorgEvent.wait()
        print(f"<{self.name}:{self.id}> is releasing critical section", flush=True)
        self.releaseTokenEvent.set()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=TokenMessage)
    def onTokenReceive(self, message: TokenMessage):
        self.reorgEvent.wait()
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

        t = time.time()
        with self.heartbitMutex:
            self.heartbitTable[message.sender] = time.time()

    def broadcast(self, message: any):
        self.reorgEvent.wait()
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> broadcasting "{message}" with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock))
    
    def ackNeededBroadcast(self, message: any):
        self.reorgEvent.wait()
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> broadcasting "{message}" asking for ACK with clock {self.clock.clock}', flush=True)
        with self.waitingForAckLock:
            self.waitingForAck = self.nbProcess
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock, ackNeeded=True))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def checkHearbits(self):
        with self.heartbitMutex:
            fails = []
            for id, lastTime in list(self.heartbitTable.items()):
                # print(f"<{self.name}:{self.id}> last heartbit from {id} {time.time() - lastTime} ago", flush=True)
                if time.time() - lastTime > Com.checkHeartbitEvery:
                    fails.append(id)
            if len(fails) > 0:
                print(f"<{self.name}:{self.id}> detected failure of process {fails}", flush=True)
                del self.heartbitTable[id]
                # self.nbProcess -= 1
                # self.nameTable[list(self.nameTable.keys())[list(self.nameTable.values()).index(id)]] = None
                PyBus.Instance().post(ReorgMessage(self.id, fails))
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent= ReorgMessage)
    def receiveReorg(self, message: ReorgMessage):
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        self.reorgEvent.clear()
        print(f"<{self.name}:{self.id}> received reorganization message, fails: {message.content}", flush=True)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=Message)
    def onReceive(self, message: Message):
        self.reorgEvent.wait()
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