class Message:
    def __init__(self, sender, content):
        self.sender = sender
        self.content = content

    def getSender(self):
        return self.sender

    def getContent(self):
        return self.content