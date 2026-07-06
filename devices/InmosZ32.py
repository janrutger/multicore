# Inmos_Z32.py 
# Start of the new Context based parrallel CPU

from collections import deque
from memory import Memory
from ucore  import Ucore

from ExecuterZ32 import _execute_cycleZ32 
# from ExecuterZ32 import HardwareContext

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

        self.contexts = []                     # <-- De order-safe lijst voor actieve threads
        self.current_context_index = 0         # <-- Start de round-robin pointer op index 0

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


                # --- STAP B: CONTROLEER OP WEZEN (DRAAD-VEILIGE GARBAGE COLLECTION) ---
                if core.coreStatus == 'VALID':
                    # 1. Check Master CPU registers
                    in_master_register = any(reg_id == core_id for reg_id in self.registers.values())
                    
                    # 2. Check ALLE threads die nog in het systeem zitten (ongeacht FSM status!)
                    in_thread_register = False
                    for ctx in self.contexts:
                        if any(reg_id == core_id for reg_id in ctx.registers.values()):
                            in_thread_register = True
                            break
                            
                    is_test_core = (self.last_test_core == core_id)
                    
                    # 3. Check of er een WORKING core is die deze core nodig heeft
                    wordt_nog_bezocht = False
                    for andere_core in self.cores:
                        if andere_core.coreStatus == 'WORKING':
                            if andere_core.arg1 == core_id or andere_core.arg2 == core_id:
                                wordt_nog_bezocht = True
                                break
                    
                    # Alleen slopen als hij écht door helemaal niemand meer geclaimd wordt
                    if not in_master_register and not in_thread_register and not is_test_core and not wordt_nog_bezocht:
                        core.coreStatus = 'IDLE'

            # 2. CONTEXT SCHEDULER: Tik exact ÉÉN actieve context aan die RUNNING is
            active_running_contexts = [c for c in self.contexts if c.fsm_state in ('FETCH', 'DECODE', 'EXECUTE', 'RUNNING')]
            
            if active_running_contexts:
                # Veiligheidsmarge: mocht de lijst gekrompen zijn, zorg dat we nooit Out-of-Bounds gaan
                if self.current_context_index >= len(active_running_contexts):
                    self.current_context_index = 0
                    
                # Pak de context die nu gegarandeerd aan de beurt is
                target_context = active_running_contexts[self.current_context_index]
                
                # Voer de FSM-stap uit voor deze specifieke context
                self._execute_cycle(self, target_context)
                
                # Schuif de pointer door naar de volgende context EN pas direct modulo toe 
                # zodat de waarde direct klopt en opgeslagen wordt voor de volgende tick.
                self.current_context_index = (self.current_context_index + 1) % len(active_running_contexts)



            # 3. Voer DAARNA de huidige hoofd-CPU instructie uit
            self._execute_cycle(self, self)



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

