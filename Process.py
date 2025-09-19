from threading import Lock, Thread

from time import sleep

from Com import Com

class Process(Thread):
    """
    Représente un processus simulé dans un environnement distribué, utilisant la communication inter-processus.

    Args:
        name (str): Nom du processus (ex: "P0", "P1", "P2").

    Attributs:
        com (Com): Objet de communication associé au processus.
        nbProcess (int): Nombre total de processus dans le système.
        alive (bool): Indique si le processus est actif.
    """

    def __init__(self,name):
        Thread.__init__(self)

        self.com = None
        
        self.nbProcess = None

        self.setName(name)

        self.alive = True
        self.start()
    
    def init(self):
        """Initialise le processus en configurant son communicateur et en récupérant le nombre total de processus."""
        self.com = Com(self.getName())
        self.nbProcess = self.com.getNbProcess()

    def run(self):
        """Exécute la logique principale du processus. Simule des interactions utilisateur."""
        self.init()

        print(f"@{self.name} - started with id {self.com.id} among {self.nbProcess} process(es)", flush=True)
        
        if self.name == "P0":
            self.com.sendTo("j'appelle P2 et je te recontacte après", "P1")

            self.com.sendToSync("J'ai laissé un message à P1, je le rappellerai après, on se sychronise tous et on attaque la partie ?", "P2")
            
            msg = self.com.recevFromSync("P2")
            print(f"@P0 - Reçu de P2 : {msg.getContent()}", flush=True)

            self.com.sendToSync("P2 est OK pour jouer, on se synchronise et c'est parti!", "P1")

            self.com.synchronize()
                
            self.com.requestSC()
            if self.com.mailbox.isEmpty():
                print(f"@P0 - Catched !", flush=True)
                self.com.ackNeededBroadcast("J'ai gagné !!!")
            else:
                msg = self.com.mailbox.getMessage()
                print(f"@P0 - {msg.getSender()} à eu le jeton en premier", flush=True)
            self.com.releaseSC()


        if self.name == "P1":
            while self.com.mailbox.isEmpty():
                print(f"@P1 - waiting for a message...", flush=True)
                sleep(0.5)
            
            msg = self.com.mailbox.getMessage()
            print(f"@P1 - Reçu de {msg.getSender()} : {msg.getContent()}", flush=True)

            msg = self.com.recevFromSync("P0")
            print(f"@P1 - Reçu de P0 : {msg.getContent()}", flush=True)

            self.com.synchronize()
            
            self.com.requestSC()
            if self.com.mailbox.isEmpty():
                print(f"@P1 - Catched !", flush=True)
                self.com.ackNeededBroadcast("J'ai gagné !!!")
            else:
                msg = self.com.mailbox.getMessage()
                print(f"@P1 - {msg.getSender()} à eu le jeton en premier", flush=True)
            self.com.releaseSC()

        if self.name == "P2":
            msg = self.com.recevFromSync("P0")
            print(f"@P2 - Reçu de P0 : {msg.getContent()}", flush=True)

            self.com.sendToSync("OK", "P0")

            self.com.synchronize()
                
            self.com.requestSC()
            if self.com.mailbox.isEmpty():
                print(f"@P2 - Catched !", flush=True)
                self.com.ackNeededBroadcast("J'ai gagné !!!")
            else:
                msg = self.com.mailbox.getMessage()
                print(f"@P2 - {msg.getSender()} à eu le jeton en premier", flush=True)
            self.com.releaseSC()

        print(f"@{self.name} - execution finished with id {self.com.id}", flush=True)

        self.stop()

    def stop(self):
        """Arrête le processus et son communicateur."""
        self.com.stop()
        self.alive = False

    def waitStopped(self):
        """Attend que le thread du processus se termine."""
        self.join()