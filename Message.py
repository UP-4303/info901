class Message:
    def __init__(self, sender: int, recipient: int, content: any, isSystem=False):
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.isSystem = isSystem

    def getSender(self) -> int:
        return self.sender

    def getContent(self) -> any:
        return self.content
    
class AutoIdMessage(Message):
    def __init__(self, sender: int, recipient: int, content: int):
        super(AutoIdMessage, self).__init__(sender, recipient, content, True)

class AckMessage(Message):
    def __init__(self, sender: int, recipient: int):
        super(AckMessage, self).__init__(sender, recipient, None, True)

class SyncMessage(Message):
    def __init__(self, sender: int, recipient: int, content: any):
        super(SyncMessage, self).__init__(sender, recipient, content, True)