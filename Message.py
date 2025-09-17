class Message:
    def __init__(self, sender: int, content: any):
        self.sender = sender
        self.content = content

    def getSender(self) -> int:
        return self.sender

    def getContent(self) -> any:
        return self.content