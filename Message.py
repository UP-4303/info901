class Message:
    def __init__(self, sender: int, recipient: int, content: any, clock: int, isSystem=False):
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.isSystem = isSystem
        self.clock = clock

    def getSender(self) -> int:
        return self.sender

    def getContent(self) -> any:
        return self.content
    
class AutoIdMessage(Message):
    def __init__(self, sender: int, recipient: int, content: int, clock: int):
        super(AutoIdMessage, self).__init__(sender, recipient, content, clock, True)

class AckMessage(Message):
    def __init__(self, sender: int, recipient: int, clock: int):
        super(AckMessage, self).__init__(sender, recipient, None, clock, True)

class SyncMessage(Message):
    def __init__(self, sender: int, recipient: int, content: any, clock: int):
        super(SyncMessage, self).__init__(sender, recipient, content, clock, True)