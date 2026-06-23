# Multicore/devices/ucore.py


class Ucore:
    def __init__(self):
        self.value    = 0       
        self.work     = 0
        self.transfer = 0
        self.status   = True
        self.matrix   = None

        self.instruction = None
        self.upc    = 0                 # Program counter

        self.coreStatus = 'IDLE'        # IDLE, WORKING, VALID

        self.arg1 = None                # Ucore ID
        self.arg2 = None                # Ucore ID



        self.ucode = {}
        self.ucode['ldv']   = ['mv_tv',  'setResult']                        # mv_tvs  the value in self.transfer in self.value
        self.ucode['stv']   = ['mv_vt', 'setResult']                        # mv_vts the value in self.value in self.fransfer
        self.ucode['status']= ['status','setResult']

        self.ucode['add']   = ['valid_v', 'valid_w', 'add', 'setResult']
        self.ucode['sub']   = ['valid_v', 'valid_w', 'sub', 'setResult']
        self.ucode['mul']   = ['valid_v', 'valid_w', 'mul', 'setResult']
        self.ucode['div']   = ['valid_v', 'valid_w', 'div', 'setResult']

        self.ucode['tstz']  = ['valid_v', 'tstz', 'setResult']               # V is zero
        self.ucode['tstn']  = ['valid_v', 'tstn', 'setResult']               # V is negative

        self.ucode['cmpe']  = ['valid_v', 'valid_w', 'cmpe',  'setResult']    # V W Equal
        self.ucode['cmpne'] = ['valid_v', 'valid_w', 'cmpne', 'setResult']    # V W NotEqual
        self.ucode['cmpgt'] = ['valid_v', 'valid_w', 'cmpgt', 'setResult']    # V W GreaterThen
        self.ucode['cmplt'] = ['valid_v', 'valid_w', 'cmplt', 'setResult']    # V W LessThen


    def initCoreMatrix(self, matrix):
        self.matrix = matrix
        self.coreStatus = 'IDLE'

    def dispatch(self, instruction, arg1=None, arg2=None):
        """Wordt aangeroepen door de hoofd-CPU om deze core aan het werk te zetten."""
        self.instruction = instruction
        self.arg1 = arg1
        self.arg2 = arg2
        self.upc = 0
        self.coreStatus = 'WORKING'

    def tick(self):

        if self.coreStatus != 'WORKING':               # check if the core is active
            return
        
        # Haal de huidige instructie op
        ucode        = self.ucode[self.instruction]    
        current_uinst = ucode[self.upc]                 

        # Splits op in opcode en operand
        if isinstance(current_uinst, tuple):
            uinstruction, uoperand = current_uinst
        else:
            uinstruction, uoperand = current_uinst, None

        

        # --- CPU <-> CORE DIRECT I/O ---
        if uinstruction == 'mv_tv':
            self.value = self.transfer
            self.upc += 1

        elif uinstruction == 'mv_vt':
            self.transfer = self.value
            self.upc += 1

        elif uinstruction == 'status':
            self.transfer = self.status
            self.upc += 1

        # --- BUS DATA-DESK (Wachten op andere cores) ---
        elif uinstruction == 'valid_v':
            # arg1 is het ID van de bron-core. Check of die al VALID is
            if self.matrix[self.arg1].coreStatus == 'VALID':
                self.value = self.matrix[self.arg1].value
                self.matrix[self.arg1].coreStatus = 'IDLE'
                self.upc += 1  # Alleen door naar de volgende stap als de data er is!

        elif uinstruction == 'valid_w':
            # arg2 is het ID van de bron-core. Check of die al VALID is
            if self.matrix[self.arg2].coreStatus == 'VALID':
                self.work = self.matrix[self.arg2].value
                self.upc += 1  # Alleen door naar de volgende stap als de data er is!

        # --- ALU REKENWERK ---
        elif uinstruction == 'add':
            self.value = self.value + self.work           # Sla direct op in value voor de buren
            self.upc += 1

        elif uinstruction == 'sub':
            self.value = self.value - self.work
            self.upc += 1

        elif uinstruction == 'mul':
            self.value = self.value * self.work
            self.upc += 1

        elif uinstruction == 'div':                       # devide by zero, results in 0, not an error
            self.value = self.value // self.work if self.work != 0 else 0
            self.upc += 1

        # --- ALU STATUS & VERGELIJKINGEN (Schrijft direct naar status/boolean) ---
        elif uinstruction == 'tstz':
            self.status = (self.value == 0)     # V en W blijven 100% intact!
            self.upc += 1

        elif uinstruction == 'tstn':
            self.status = (self.value < 0)
            self.upc += 1

        elif uinstruction == 'cmpe':
            self.status = (self.value == self.work)
            self.upc += 1

        elif uinstruction == 'cmpne':
            self.status = (self.value != self.work)
            self.upc += 1

        elif uinstruction == 'cmpgt':
            self.status = (self.value > self.work)
            self.upc += 1

        elif uinstruction == 'cmplt':
            self.status = (self.value < self.work)
            self.upc += 1

        # --- MICRO BRANCHING LOGICA ---
        elif uinstruction == 'bra_always':
            self.upc += uoperand  # Overschrijf de upc direct met het doeladres
            return                # Zorg dat de upc += 1 aan het einde wordt overgeslagen!

        elif uinstruction == 'bra_false':
            if not self.status:  # Als de test False heeft opgeleverd
                self.upc += uoperand
                return
            else:
                self.upc += 1    # Conditie niet waar? Loop gewoon door naar de volgende stap

        # --- AFRONDING EN PUBLICATIE ---
        elif uinstruction == 'setResult':
            self.coreStatus = 'VALID'
            self.upc = 0