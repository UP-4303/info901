from Mailbox import Mailbox

class Com:
    def __init__(self):
        self.mailbox = Mailbox()
    
    def getNbProcess(self):
        pass

    def getMyId(self):
        pass

    def sendTo(self, message, destId):
        pass

    def sendToSync(self, message, destId):
        pass

    def recevFromSync(self, message, srcId):
        pass

    def synchronize(self):
        pass

    def requestSC(self):
        pass

    def releaseSC(self):
        pass

    def broadcast(self, message):
        pass

