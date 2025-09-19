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
    """
    Com permet de gérer la communication entre processus, elle inclue l'envoie et la réception des messages synchrone et asynchrone via une boite aux lettres,
    la gestion des tokens, l'attente de barrière, des heartbeats et de la réorganisation dans un système distribué.

    Class Attributes:
        timeout (int |float): Temps d'attente en secondes pour la génération d'ID.
        maxRand (int): Valeur maximale pour la génération aléatoire des numéros d'ID.
        sendHeartbitEvery (int |float): Intervalle en secondes pour l'envoi des heartbeats.
        checkHeartbitEvery (int |float): Intervalle en secondes pour la vérification des heartbeats.

    Args:
        name (str): Le nom du processus.
            /!\\ Il est de la responsabilité des utilisateurs de donner un nom unique pour chaque processus /!\\
            
    Attributs:
        mailbox (Mailbox): La boîte aux lettres du processus pour stocker les messages reçus.
        clock (LamportClock): L'horloge de Lamport pour la gestion des horloges logiques. Est ignorée sur les messages système, à l'envoi comme à la réception.
        name (str): Le nom du processus.
        nameTable (dict[str, int]): Table de correspondance entre les noms des processus et leurs IDs.
        heartbitMutex (Lock): Mutex protégeant l'accès à la table des heartbeats.
        heartbitTable (dict[int, float]): Table des derniers timestamps de réception des heartbeats.
        receivedNumbers (list[tuple[int, str]]): Liste des numéros reçus pour la génération d'ID. Utilisée uniquement pour la génération des IDs à l'initialisation.
        receivedNumbersMutex (Lock): Mutex pour protéger l'accès à receivedNumbers.
        id (int | None): L'ID unique du processus.
        nbProcess (int | None): Le nombre total de processus dans le système.
        ackEvent (Event): Événement pour la gestion des ACK.
        waitingForAck (int): Compteur du nombre d'ACK en attente.
        waitingForAckLock (Lock): Mutex pour protéger l'accès à waitingForAck.
        syncEvent (Event): Événement pour la gestion des messages synchronisés.
        receiveLock (Lock): Mutex pour protéger la réception des messages synchronisés.
        syncMessage (SyncMessage | None): Le message synchronisé reçu.
        requestTokenEvent (Event): Événement pour la réception lors de l'attente de token.
        releaseTokenEvent (Event): Événement pour la libération du token.
        waitingForToken (bool): Indique si le processus attend le token.
        joinEvent (Event): Événement pour la gestion des barrières de synchronisation.
        joiningIds (set): Ensemble des IDs des processus ayant rejoint la barrière.
        alive (Event): Événement indiquant si le processus est actif.
        initializedEvent (Event): Événement indiquant si le processus est initialisé.
        reorgEvent (Event): Événement indiquant si une réorganisation est attendue ou en cours.
        killEvent (Event): Événement pour arrêter les tâches de fond.
        sendHeartbitTask (LoopTask): Tâche de fond pour l'envoi périodique des heartbeats.
        checkHeartbitTask (LoopTask): Tâche de fond pour la vérification périodique des heartbeats.
    """
    timeout = 1
    maxRand = 100
    sendHeartbitEvery = 1
    checkHeartbitEvery = 5

    def __init__(self, name: str):
        """
        Initialise une instance de Com avec le nom du processus, les structures de synchronisation,
        les événements, la boîte aux lettres, l'horloge logique et démarre les tâches de fond.
        """
        self.mailbox = Mailbox()
        self.clock = LamportClock()
        PyBus.Instance().register(self, self)

        self.name = name
        self.nameTable = dict[str, int]()
        self.heartbitMutex = Lock()
        self.heartbitTable = dict[int, float]()

        self.receivedNumbers: list[tuple[int, str]] = []
        self.receivedNumbersMutex = Lock()
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
        self.sendHeartbitTask = LoopTask(Com.sendHeartbitEvery, self.sendHeartbit, (), self.killEvent)
        self.chackHeartbitTask = LoopTask(Com.checkHeartbitEvery, self.checkHearbits, (), self.killEvent)
    
    def stop(self):
        """
        Arrête le processus en désactivant les événements de vie et de boucle.
        """
        self.alive.clear()
        self.killEvent.set()
        self.sendHeartbitTask.join()
        self.chackHeartbitTask.join()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=AutoIdMessage)
    def onAutoIdReceive(self, message: AutoIdMessage):
        """
        Handler pour la réception d'un message système de génération d'ID.
        Ajoute le numéro reçu à la liste des numéros reçus.
        """
        with self.receivedNumbersMutex:
            self.receivedNumbers.append(message.content)

    def autoId(self) -> None:
        """
        Génère un identifiant unique pour le processus et construit la table des noms.
        """
        self.alive.set()

        myNumber = None
        sleep(Com.timeout)
        while True:
            if myNumber == None:
                myNumber = randint(0, Com.maxRand)
                PyBus.Instance().post(AutoIdMessage([myNumber, self.name]))
            sleep(Com.timeout)
            
            with self.receivedNumbersMutex:
                numbers = [item[0] for item in self.receivedNumbers]
            duplicate = [num for num, count in collections.Counter(numbers).items() if count > 1]
            if len(duplicate) > 0:
                with self.receivedNumbersMutex:
                    self.receivedNumbers = [item for item in self.receivedNumbers if not item[0] in duplicate]
                if myNumber in duplicate:
                    myNumber = None
            else:
                break

        with self.receivedNumbersMutex:
            self.receivedNumbers.sort()
            for i, item in enumerate(self.receivedNumbers):
                self.nameTable[item[1]] = i
                if item[0] == myNumber and item[1] == self.name:
                    self.id = i

            print(f"<{self.name}:{self.id}> nameTable: {self.nameTable}", flush=True)
            self.nbProcess = len(self.receivedNumbers)
    
    def startToken(self) -> None:
        """
        Démarre la circulation du token si le processus est le dernier.
        """
        if self.id == self.nbProcess - 1:
            sleep(Com.timeout)
            PyBus.Instance().post(TokenMessage(self.id, 0))

    def getNbProcess(self) -> int:
        """
        Retourne le nombre total de processus dans le système.
        """
        return self.nbProcess

    def sendTo(self, message: any, dest: str):
        """
        Envoie un message asynchrone à un destinataire spécifique.
        """
        self.reorgEvent.wait()
        if dest not in self.nameTable:
            print(f"<{self.name}:{self.id}> ERROR: destination {dest} unknown", flush=True)
            return

        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> sending "{message}" to <{dest}:{self.nameTable[dest]}> with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, self.nameTable[dest], message, self.clock.clock))

    def sendToSync(self, message: any, dest: str):
        """
        Envoie un message synchronisé à un destinataire et attend l'ACK.
        """
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
        """
        Attend la réception d'un message synchronisé depuis une source spécifique et renvoie le message reçu.
        """
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
        """
        Handler pour la réception d'un message d'ACK.
        """
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
        """
        Handler pour la réception d'un message synchronisé.
        """
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
        """
        Synchronise le processus avec tous les autres.
        """
        self.reorgEvent.wait()
        print(f"<{self.name}:{self.id}> is synchronizing", flush=True)
        PyBus.Instance().post(JoinMessage(self.id))
        self.joinEvent.wait()
        self.joinEvent.clear()
        self.joiningIds.clear()
        print(f"<{self.name}:{self.id}> synchronized with {self.nbProcess - 1} others", flush=True)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=JoinMessage)
    def onJoinRecieve(self, message: JoinMessage):
        """
        Handler pour la réception d'un message de synchronisation.
        """
        self.reorgEvent.wait()
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        self.joiningIds.add(message.sender)
        print(f"<{self.name}:{self.id}> received join from {message.sender}, currently at {len(self.joiningIds)}/{self.nbProcess}", flush=True)
        if len(self.joiningIds) == self.nbProcess:
            self.joinEvent.set()

    def requestSC(self):
        """
        Demande l'accès à la section critique en attendant le token.
        """
        self.reorgEvent.wait()
        print(f"<{self.name}:{self.id}> is requesting critical section", flush=True)
        self.waitingForToken = True
        self.releaseTokenEvent.clear()
        self.requestTokenEvent.wait()
        self.requestTokenEvent.clear()
        print(f"<{self.name}:{self.id}> got the token", flush=True)

    def releaseSC(self):
        """
        Libère la section critique et le token.
        """
        self.reorgEvent.wait()
        print(f"<{self.name}:{self.id}> is releasing critical section", flush=True)
        self.releaseTokenEvent.set()

    @subscribe(threadMode= Mode.PARALLEL, onEvent=TokenMessage)
    def onTokenReceive(self, message: TokenMessage):
        """
        Handler pour la réception d'un message TokenMessage.
        Gère la circulation du token et l'accès à la section critique.
        """
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
        """
        Envoie un message Heartbit pour signaler que le processus est vivant.
        """
        PyBus.Instance().post(HeartbitMessage(self.id))
    
    @subscribe(threadMode= Mode.PARALLEL, onEvent= HeartbitMessage)
    def receiveHeartbit(self, message: HeartbitMessage):
        """
        Handler pour la réception d'un message de heartbeat.
        """
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        t = time.time()
        with self.heartbitMutex:
            self.heartbitTable[message.sender] = time.time()

    def broadcast(self, message: any):
        """
        Diffuse un message asynchrone à tous les processus.
        """
        self.reorgEvent.wait()
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> broadcasting "{message}" with clock {self.clock.clock}', flush=True)
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock))
    
    def ackNeededBroadcast(self, message: any):
        """
        Diffuse un message à tous les processus en attendant un ACK de chacun.
        """
        self.reorgEvent.wait()
        self.clock.inc_clock()
        print(f'<{self.name}:{self.id}> broadcasting "{message}" asking for ACK with clock {self.clock.clock}', flush=True)
        with self.waitingForAckLock:
            self.waitingForAck = self.nbProcess
        PyBus.Instance().post(Message(self.id, None, message, self.clock.clock, ackNeeded=True))
        self.ackEvent.wait()
        self.ackEvent.clear()

    def checkHearbits(self):
        """
        Vérifie les heartbeats reçus et détecte les processus défaillants.
        """
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
        """
        Handler pour la réception d'un message de réorganisation.
        Bloque les autres opérations pendant la réorganisation.
        """
        if not self.alive.is_set():
            return
        self.initializedEvent.wait()

        self.reorgEvent.clear()
        print(f"<{self.name}:{self.id}> received reorganization message, fails: {message.content}", flush=True)

    @subscribe(threadMode= Mode.PARALLEL, onEvent=Message)
    def onReceive(self, message: Message):
        """
        Handler pour la réception d'un message générique.
        Met à jour l'horloge, ajoute le message à la boîte aux lettres et gère les ACK si nécessaire.
        """
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