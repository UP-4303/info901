from threading import Lock, Thread

from time import sleep

from Com import Com

class Process(Thread):
    
    def __init__(self,name):
        Thread.__init__(self)

        self.com = None
        
        self.nbProcess = None

        self.myId = None
        self.setName(name)

        self.alive = True
        self.start()
    
    def init(self):
        self.com = Com()
        self.nbProcess = self.com.getNbProcess()
        self.myId = self.com.getMyId()

    def run(self):
        self.init()

        print(f"{self.getName()} started with id {self.myId} among {self.nbProcess} process(es)", flush=True)
        
        if self.myId == 0:
            self.com.sendTo("j'appelle 2 et je te recontacte après", 1)
            
            self.com.sendToSync("J'ai laissé un message à 1, je le rappellerai après, on se sychronise tous et on attaque la partie ?", 2)
            msg = self.com.recevFromSync(2)
            print(f"Process 0 Reçu de 2 : {msg.getContent()}", flush=True)
            
            self.com.sendToSync("2 est OK pour jouer, on se synchronise et c'est parti!",1)
                
            self.com.synchronize()
                
            self.com.requestSC()
            if self.com.mailbox.isEmpty():
                print(f"Process 0 Catched !", flush=True)
                self.com.ackNeededBroadcast("J'ai gagné !!!")
            else:
                msg = self.com.mailbox.getMessage()
                print(f"Process 0 {msg.getSender()} à eu le jeton en premier", flush=True)
            self.com.releaseSC()


        if self.myId == 1:
            while self.com.mailbox.isEmpty():
                sleep(0.5)
            msg = self.com.mailbox.getMessage()
            print(f"Process 1 Reçu de "+str(msg.getSender())+" : "+str(msg.getContent()), flush=True)

            msg = self.com.recevFromSync(0)
            print(f"Process 1 Reçu de 0 : {msg.getContent()}", flush=True)

            self.com.synchronize()
            
            self.com.requestSC()
            if self.com.mailbox.isEmpty():
                print(f"Process 1 Catched !", flush=True)
                self.com.ackNeededBroadcast("J'ai gagné !!!")
            else:
                msg = self.com.mailbox.getMessage()
                print(f"Process 1 {msg.getSender()} à eu le jeton en premier", flush=True)
            self.com.releaseSC()
            
        if self.myId == 2:
            msg = self.com.recevFromSync(0)
            print(f"Process 2 Reçu de 0 : {msg.getContent()}", flush=True)

            self.com.sendToSync("OK", 0)

            self.com.synchronize()
                
            self.com.requestSC()
            if self.com.mailbox.isEmpty():
                print(f"Process 2 Catched !", flush=True)
                self.com.ackNeededBroadcast("J'ai gagné !!!")
            else:
                msg = self.com.mailbox.getMessage()
                print(f"Process 2 {msg.getSender()} à eu le jeton en premier", flush=True)
            self.com.releaseSC()

        print(f"{self.getName()} execution finished", flush=True)

        self.stop()

    def stop(self):
        self.com.alive = False
        self.alive = False

    def waitStopped(self):
        self.join()