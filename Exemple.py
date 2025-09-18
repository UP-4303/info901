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
        
        loop = 0
        while self.alive:
            print(self.getName() + " Loop: " + str(loop), flush=True)
            sleep(1)

            if self.myId == 0:
                self.com.sendTo("j'appelle 2 et je te recontacte après", 1)
                
                self.com.sendToSync("J'ai laissé un message à 1, je le rappellerai après, on se sychronise tous et on attaque la partie ?", 2)
                msg = self.com.recevFromSync(2)
                print("<0> Reçu de 2 : "+str(msg.getContent()))
               
                self.com.sendToSync("2 est OK pour jouer, on se synchronise et c'est parti!",1)
                    
                self.com.synchronize()
                    
                self.com.requestSC()
                if self.com.mailbox.isEmpty():
                    print("Catched !", flush=True)
                    self.com.broadcast("J'ai gagné !!!")
                else:
                    msg = self.com.mailbox.getMessage()
                    print(str(msg.getSender())+" à eu le jeton en premier", flush=True)
                self.com.releaseSC()


            if self.myId == 1:
                if not self.com.mailbox.isEmpty():
                    msg = self.com.recevFromSync(0)
                    print("<1> Reçu de 0 : "+str(msg.getContent()))

                    self.com.synchronize()
                    
                    self.com.requestSC()
                    if self.com.mailbox.isEmpty():
                        print("Catched !", flush=True)
                        self.com.broadcast("J'ai gagné !!!")
                    else:
                        msg = self.com.mailbox.getMessage()
                        print(str(msg.getSender())+" à eu le jeton en premier", flush=True)
                    self.com.releaseSC()
                    
            if self.myId == 2:
                msg = self.com.recevFromSync(0)
                print("<2> Reçu de 0 : "+str(msg.getContent()))

                self.com.sendToSync("OK", 0)

                self.com.synchronize()
                    
                self.com.requestSC()
                if self.com.mailbox.isEmpty():
                    print("Catched !", flush=True)
                    self.com.broadcast("J'ai gagné !!!")
                else:
                    msg = self.com.mailbox.getMessage()
                    print(str(msg.getSender())+" à eu le jeton en premier", flush=True)
                self.com.releaseSC()

            loop+=1
        print(self.getName() + " stopped", flush=True)

    def stop(self):
        self.alive = False
        self.join()