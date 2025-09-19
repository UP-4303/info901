from Message import Message
from threading import RLock

class Mailbox:
    def __init__(self):
        self.messages: list[Message] = []
        self.lock = RLock()

    def isEmpty(self) -> bool:
        with self.lock:
            return len(self.messages) == 0

    def getMessage(self) -> Message | None:
        with self.lock:
            if not self.isEmpty():
                return self.messages.pop(0)
            return None

    def addMessage(self, message: Message) -> None:
        with self.lock:
            self.messages.append(message)