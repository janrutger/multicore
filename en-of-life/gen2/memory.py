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

# class Memory:
#     def __init__(self, size=1024, bits=64):
#         self.memory = [0] * size
#         self.mask = (1 << bits) - 1  # De harde grens: 0xFFFFFFFFFFFFFFFF

#     def memRead(self, adres):
#         return self.memory[adres]
    
#     def memWrite(self, value, adres):
#         if value > self.mask:
#             print(f"[WAARSCHUWING] Bignum gedetecteerd op adres {adres}: {value} (Grens: {self.mask})")
#         self.memory[adres] = value & self.mask

#     def memSize(self):
#         return len(self.memory)