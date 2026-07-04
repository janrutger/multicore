# Inmos_Z32.py 
# Start of the new Context based parrallel CPU

from collections import deque
from memory import Memory
from ucore  import Ucore

from ExecuterZ32 import _execute_cycleZ32

# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class CPU:
    def __init__(self):
        self.memory = Memory(size=1024)

        self._execute_cycle = _execute_cycleZ32

        # Stap 1: Maak alle cores onafhankelijk aan
        self.cores = [Ucore() for _ in range(32)]

        # Stap 2: Koppel ze aan de matrix-omgeving (de lijst zelf)
        for core in self.cores:
            core.initCoreMatrix(self.cores)

        self.last_active_core = None
        self.last_test_core   = None        # Slaat specifiek de Core-ID op van de LAATSTE test/vergelijking


        # register setup
        self.PC  = 0                           # Program counter
        self.SP  = self.memory.memSize() - 1   # Stackpointer
        self.status = 1                        # Status flag is true

        self.fsm_state = 'FETCH'             # FETCH, DECODE, EXECUTE
        self.MIR       = None                # Memory Instruction Register (onze huidige integer)

        # Tijdelijk gedecodede variabelen die we bewaren tussen de ticks door
        self.decoded_opcode = 0
        self.decoded_reg1   = 0
        self.decoded_arg2   = 0

        # Registers bevatten de Core-ID die de waarde vertegenwoordigt
        self.registers = {i: None for i in range(10)}      

        # --- DYNAMISCH CORE BEHEER ---
        # We stoppen alle Core ID's (0 t/m 15) in de vrije wachtrij
        self.free_cores = deque(range(32))


    def tick(self):
            """Voert één volledige kloksnelheid-cyclus uit voor het hele systeem."""
            
            # 1. Geef alle cores in de matrix de ruimte om hun microstep te doen
            for core_id, core in enumerate(self.cores):
                core.tick()

                # --- STAP A: Geef de reeds IDLE cores terug aan de wachtrij ---
                if core.coreStatus == 'IDLE' and core_id not in self.free_cores:
                    self.free_cores.append(core_id)

                # --- STAP B: CONTROLEER OP WEZEN (GARBAGE COLLECTION) ---
                if core.coreStatus == 'VALID':
                    in_register = any(reg_id == core_id for reg_id in self.registers.values())
                    is_test_core = (self.last_test_core == core_id)
                    
                    # Check of er een WORKING core is die deze core_id als arg1 of arg2 heeft
                    wordt_nog_bezocht = False
                    for andere_core in self.cores:
                        if andere_core.coreStatus == 'WORKING':
                            if andere_core.arg1 == core_id or andere_core.arg2 == core_id:
                                wordt_nog_bezocht = True
                                break
                    
                    # Alleen opruimen als hij écht nergens meer aan gekoppeld is
                    if not in_register and not is_test_core and not wordt_nog_bezocht:
                        core.coreStatus = 'IDLE'


            # 2. Voer DAARNA de huidige hoofd-CPU instructie uit
            self._execute_cycle(self)



    def is_completely_idle(self):
        """Controleert of de CPU op HALT staat én alle cores klaar zijn met rekenen."""
        if self.fsm_state != 'HALT':
            return False
            
        # Check of er nog ergens een core aan het werk is
        for core in self.cores:
            if core.coreStatus == 'WORKING':
                return False
                
        # Als de CPU op HALT staat en geen enkele core is WORKING, zijn we klaar!
        return True

