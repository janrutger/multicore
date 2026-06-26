# Multicore/devices/ucore.py
"""
===============================================================================
                       MICROPROGRAMMERING GIDS VOOR DE UCORE
===============================================================================

De Ucore is een minimalistische, asynchrone execution unit binnen de STERN-matrix.
In plaats van een grote traditionele registerset, programmeer je de Ucore direct
op microcode-niveau (`self.ucode`) met behulp van drie interne registers, een 
status-vlag en dedicated hardware-registers voor signed arithmetic (teken-bewustzijn).

1. DE INTERNE ARCHITECTUUR (REGISTERS)
--------------------------------------
* `V` (Value)   : De primaire invoer/uitvoer voor data en buren-communicatie.
* `W` (Work)    : De secundaire invoer voor ALU-operaties (rekenwerk).
* `T` (Transfer): De accumulator waar tussenstanden en loops in worden opgebouwd.
* `Status`      : Een boolean vlag (True/False) die het resultaat van tests bevat.
* `sign_v / sign_w` : Interne hardware-latches die het oorspronkelijke teken (+/-)
                      van de invoerdata onthouden voor signed operaties.

2. INSTRUCTIE-SYNTAX & SYSTEMATIEK
----------------------------------
Micro-instructies worden opeenvolgend uitgevoerd via de interne micro-PC (`upc`).
Instructies kunnen een platte string zijn, of een tuple `(instructie, operand)`
wanneer er een sprong-offset (micro-branch) nodig is.

Datatransport gebruikt de strikte systematiek: `mv_[bron][doel]`
* `mv_tv` : Kopieer data van Transfer (T) naar Value (V).
* `mv_vt` : Kopieer data van Value    (V) naar Transfer (T).
* `mv_wt` : Kopieer data van Work     (W) naar Transfer (T).
* `mv_vw` : Kopieer data van Value    (V) naar Work     (W).
* `mv_tw` : Kopieer data van Transfer (T) naar Work     (W).

3. MICROCODE INSTRUCTIESET
--------------------------
De decoder ondersteunt de volgende low-level operaties:

AANSTURING & SYNCHRONISATIE:
* `valid_v`   : Blokkeer de core (stall) tot Arg1/A geldig is. Slaat het teken op.
* `valid_w`   : Blokkeer de core (stall) tot Arg2/B geldig is. Slaat het teken op.
* `setResult` : Activeert de output-fase: zet coreStatus op 'VALID'.

ALU / REKENWERK (DIRECT EN INDIRECT):
* `add` / `sub` / `mul` / `div` : Voer operatie uit op V en W, sla op in V.
* `clr_t`     : Reset de accumulator (`T = 0`).
* `dec_v`     : Verlaag de teller direct met één (`V = V - 1`).
* `add_tw`    : Accumuleer: tel de waarde van Work op bij Transfer (`T = T + W`).

SIGNED OPERATIONS (TEKEN-LOGICA):
* `abs_v`     : Maak de waarde in V absoluut (`V = abs(V)`).
* `abs_w`     : Maak de waarde in W absoluut (`W = abs(W)`).
* `sign_vxor` : Pas het correcte eindteken toe op basis van vermenigvuldigings-
                wetten: als `sign_v != sign_w`, wordt V negatief (`V = -abs(V)`).

TESTS (BEÏNVLOEDEN DE self.status VLAG):
* `tstz`      : Controleer of V nul is (`V == 0`).
* `tstn`      : Controleer of V negatief is (`V < 0`).
* `cmplt`     : Controleer of V kleiner is dan W (`V < W`).
* `cmpe` / `cmpne` / `cmpgt` : Traditionele vergelijkingen tussen V en W.

MICRO-BRANCHING (SPRONG-LOGICA):
* `bra_always`: Spring direct met de opgegeven relatieve operand-offset.
* `bra_true`  : Spring alleen als `self.status` WAAR (True) is.
* `bra_false` : Spring alleen als `self.status` ONWAAR (False) is.

===============================================================================
"""

from opcodes import MICROCODE_ROM

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

        self.sign_v = False  # Onthoudt of de originele V negatief was
        self.sign_w = False  # Onthoudt of de originele W negatief was

        # Verwijs simpelweg naar de centrale ROM in plaats van een eigen dict bouwen!
        self.ucode = MICROCODE_ROM


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

        elif uinstruction == 'mv_wt':
            self.transfer = self.work
            self.upc += 1

        elif uinstruction == 'mv_tw':
            self.work = self.transfer
            self.upc += 1

        elif uinstruction == 'mv_vw':
            self.value = self.work      # Destination = Value, Source = Work
            self.upc += 1

        elif uinstruction == 'status':
            self.transfer = self.status
            self.upc += 1

        # --- BUS DATA-DESK (Wachten op andere cores) ---
        elif uinstruction == 'valid_v':
            # arg1 is het ID van de bron-core. Check of die al VALID is
            if self.matrix[self.arg1].coreStatus == 'VALID':
                # self.value = self.matrix[self.arg1].value
                # self.matrix[self.arg1].coreStatus = 'IDLE'
                # self.upc += 1  # Alleen door naar de volgende stap als de data er is!
                raw_val = self.matrix[self.arg1].value
                self.sign_v = (raw_val < 0)  # HIER registreren we het teken!
                self.value = raw_val
                self.matrix[self.arg1].coreStatus = 'IDLE'
                self.upc += 1

        elif uinstruction == 'valid_w':
            # arg2 is het ID van de bron-core. Check of die al VALID is
            if self.matrix[self.arg2].coreStatus == 'VALID':
                # self.work = self.matrix[self.arg2].value
                # self.upc += 1  # Alleen door naar de volgende stap als de data er is!
                raw_val = self.matrix[self.arg2].value
                self.sign_w = (raw_val < 0)  # HIER registreren we het teken!
                self.work = raw_val
                self.upc += 1

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

        # logische functies
        elif uinstruction == 'xor_vw':
            self.value = self.value ^ self.work
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

        elif uinstruction == 'bra_true':
            if self.status:  # Spring als de test WAAR was (bijv. V == 0)
                self.upc += uoperand
                return
            else:
                self.upc += 1
        
        # --- NIEUWE DIRECTE REGISTER MANIPULATIE ---
        elif uinstruction == 'clr_t':
            self.transfer = 0
            self.upc += 1

        elif uinstruction == 'dec_v':
            self.value -= 1
            self.upc += 1

        elif uinstruction == 'add_tw':
            # De pure accumulator actie: tel W op bij T
            self.transfer = self.transfer + self.work
            self.upc += 1

        elif uinstruction == 'abs_v':
            self.value = abs(self.value)
            self.upc += 1

        elif uinstruction == 'abs_w':
            self.work = abs(self.work)
            self.upc += 1

        elif uinstruction == 'sign_vxor':
            # Conditional Negate: als de originele tekens ongelijk waren, xor ze
            if self.sign_v != self.sign_w:
                self.value = -abs(self.value)
            self.upc += 1

        

        # --- AFRONDING EN PUBLICATIE ---
        elif uinstruction == 'setResult':
            self.coreStatus = 'VALID'
            self.upc = 0