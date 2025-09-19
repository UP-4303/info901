from threading import Thread, Event
from time import sleep

class LoopTask(Thread):
    """
    Thread exécutant périodiquement une tâche jusqu'à réception d'un signal d'arrêt.

    Args:
        repeatEvery (float | int): Intervalle de répétition en secondes entre chaque exécution de la tâche.
        callback (callable): Fonction à appeler à chaque itération.
        parameters (tuple): Paramètres à passer à la fonction callback.
        killEvent (Event): Événement utilisé pour arrêter la boucle.
    """

    def __init__(self, repeatEvery: float | int, callback, parameters, killEvent: Event):
        super(LoopTask, self).__init__()
        self.repeatEvery = repeatEvery
        self.callback = callback
        self.parameters = parameters
        self.killEvent = killEvent
        self.start()

    def run(self):
        """Exécute le callable stocké dans self.callback périodiquement jusqu'à ce que self.killEvent soit set."""
        while not self.killEvent.is_set():
            self.callback(*self.parameters)
            self.killEvent.wait(self.repeatEvery)