from random import randint

class Message:
    def __init__(self, sender: int, recipient: int, content: any, clock: int, isSystem=False, ackNeeded=False):
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.isSystem = isSystem
        self.clock = clock
        self.ackNeeded = ackNeeded

    def getSender(self) -> int:
        return self.sender

    def getContent(self) -> any:
        return self.content
    
class AutoIdMessage(Message):
    def __init__(self, sender: int, recipient: int, content: int):
        super(AutoIdMessage, self).__init__(sender, recipient, content, 0, True)

class AckMessage(Message):
    def __init__(self, sender: int, recipient: int):
        super(AckMessage, self).__init__(sender, recipient, None, 0, True)

class SyncMessage(Message):
    def __init__(self, sender: int, recipient: int, content: any, clock: int):
        super(SyncMessage, self).__init__(sender, recipient, content, clock, ackNeeded=True)

class TokenMessage(Message):
    def __init__(self, sender: int, recipient: int):
        super(TokenMessage, self).__init__(sender, recipient, randint(0,100), 0, True)

class JoinMessage(Message):
    def __init__(self, sender: int):
        super(JoinMessage, self).__init__(sender, None, None, 0, True)

class HeartbitMessage(Message):
    def __init__(self, sender: int):
        super(HeartbitMessage,self).__init__(sender, None, None, 0, True)