from Message import Message

class Mailbox:
    def __init__(self):
        self.messages: list[Message] = []

    def isEmpty(self):
        return len(self.messages) == 0
    
    def getMsg(self) -> Message | None: 
        return self.messages.pop(0) if not self.isEmpty() else None
    
    def getMessage(self):
        pass