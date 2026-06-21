# memory.py


class Memory:
    def __init__(self, size=1024):
        self.memory = [0] * size


    def memRead(self, adres):
        return self.memory[adres]
    
    def memWrite(self, value, adres):
        self.memory[adres] = value

    def memSize(self):
        return len(self.memory)