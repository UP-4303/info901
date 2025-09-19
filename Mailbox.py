from Message import Message
from threading import RLock

class Mailbox:
    """
    Classe représentant une boîte aux lettres pour stocker et gérer les messages reçus par un processus.
    Utilise un verrou pour garantir la sécurité des accès concurrents.
    """
    def __init__(self):
        """
        Initialise une boîte aux lettres vide et un verrou réentrant pour la synchronisation.
        """
        self.messages: list[Message] = []
        self.lock = RLock()

    def isEmpty(self) -> bool:
        """
        Vérifie si la boîte aux lettres est vide.
        Returns:
            bool: True si la boîte est vide, False sinon.
        """
        with self.lock:
            return len(self.messages) == 0

    def getMessage(self) -> Message | None:
        """
        Récupère et retire le premier message de la boîte aux lettres.
        Returns:
            Message | None: Le message retiré ou None si la boîte est vide.
        """
        with self.lock:
            if not self.isEmpty():
                return self.messages.pop(0)
            return None

    def addMessage(self, message: Message) -> None:
        """
        Ajoute un message à la boîte aux lettres.
        Args:
            message (Message): Le message à ajouter.
        """
        with self.lock:
            self.messages.append(message)