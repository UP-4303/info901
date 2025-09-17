from Message import Message

class Mailbox:
    def __init__(self):
        self.messages: list[Message] = []

    def isEmpty(self) -> bool:
        return len(self.messages) == 0
    
    def getMessage(self) -> Message | None: 
        return self.messages.pop(0) if not self.isEmpty() else None
