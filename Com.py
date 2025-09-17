from Mailbox import Mailbox
from Message import Message

class Com:
    def __init__(self):
        self.mailbox = Mailbox()
    
    def getNbProcess(self) -> int:
        pass

    def getMyId(self) -> int:
        pass

    def sendTo(self, message: any, destId: int):
        pass

    def sendToSync(self, message: any, destId: int):
        pass

    def recevFromSync(self, srcId: int) -> Message:
        pass

    def synchronize(self):
        pass

    def requestSC(self):
        pass

    def releaseSC(self):
        pass

    def broadcast(self, message: any):
        pass

