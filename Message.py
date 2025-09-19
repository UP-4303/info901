from random import randint

class Message:
    """
    Classe de base pour tous les messages échangés entre processus.

    Args:
        sender (int): Identifiant du processus émetteur.
        recipient (int): Identifiant du processus récepteur.
        content (any): Contenu du message.
        clock (int): Horloge logique associée au message.
        isSystem (bool): Indique si le message est un message système.
        ackNeeded (bool): Indique si le message nécessite un accusé de réception (ACK).
    """
    def __init__(self, sender: int, recipient: int, content: any, clock: int, isSystem=False, ackNeeded=False):
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.isSystem = isSystem
        self.clock = clock
        self.ackNeeded = ackNeeded

    def getSender(self) -> int:
        return self.sender

    def getContent(self) -> any:
        return self.content
    
class AutoIdMessage(Message):
    """
    Message système utilisé pour l'attribution automatique d'identifiants aux processus.

    Args:
        content (tuple[int, str]): Tuple contenant un nombre aléatoire et le nom du processus.
    """
    def __init__(self, content: tuple[int, str]):
        super(AutoIdMessage, self).__init__(None, None, content, 0, True)

class AckMessage(Message):
    """
    Message d'accusé de réception (ACK) pour la synchronisation des échanges.

    Args:
        sender (int): Identifiant du processus émetteur.
        recipient (int): Identifiant du processus récepteur.
    """
    def __init__(self, sender: int, recipient: int):
        super(AckMessage, self).__init__(sender, recipient, None, 0, True)

class SyncMessage(Message):
    """
    Message utilisé pour les échanges synchronisés entre processus, nécessitant un ACK.

    Args:
        sender (int): Identifiant du processus émetteur.
        recipient (int): Identifiant du processus récepteur.
        content (any): Contenu du message.
        clock (int): Horloge logique associée au message.
    """
    def __init__(self, sender: int, recipient: int, content: any, clock: int):
        super(SyncMessage, self).__init__(sender, recipient, content, clock, ackNeeded=True)

class TokenMessage(Message):
    """
    Message système pour la gestion et la circulation du token dans l'algorithme de section critique.

    Args:
        sender (int): Identifiant du processus émetteur.
        recipient (int): Identifiant du processus récepteur.
    """
    def __init__(self, sender: int, recipient: int):
        super(TokenMessage, self).__init__(sender, recipient, randint(0,100), 0, True)

class JoinMessage(Message):
    """
    Message utilisé pour la synchronisation de barrière entre processus.

    Args:
        sender (int): Identifiant du processus émetteur.
    """
    def __init__(self, sender: int):
        super(JoinMessage, self).__init__(sender, None, None, 0, True)

class HeartbitMessage(Message):
    """
    Message système pour signaler que le processus est vivant (heartbeat).

    Args:
        sender (int): Identifiant du processus émetteur.
    """
    def __init__(self, sender: int):
        super(HeartbitMessage,self).__init__(sender, None, None, 0, True)

class ReorgMessage(Message):
    """
    Message système pour indiquer une réorganisation suite à la détection de processus défaillants.

    Args:
        sender (int): Identifiant du processus émetteur.
        fails (list[int]): Liste des identifiants des processus défaillants.
    """
    def __init__(self, sender: int, fails: list[int]):
        super(ReorgMessage,self).__init__(sender, None, fails, 0, True)