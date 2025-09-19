from threading import Lock

class LamportClock:
    """
    Implémentation d'une horloge logique de Lamport pour la synchronisation des événements dans un système distribué.
    """

    def __init__(self):
        """
        Initialise l'horloge Lamport à zéro et crée un verrou pour la synchronisation des accès.
        """
        self.semaphore = Lock()
        self.clock = 0

    def inc_clock(self):
        """
        Incrémente la valeur de l'horloge Lamport de 1.
        """
        with self.semaphore:
            self.clock += 1

    def sync(self, other: int):
        """
        Synchronise l'horloge Lamport avec une autre valeur reçue.
        La nouvelle valeur sera max(self.clock, other) + 1.
        Args:
            other (int): Valeur de l'horloge reçue d'un autre processus.
        """
        with self.semaphore:
            self.clock = max(self.clock, other)+1