# Inmos_Z32A.py 
# Start of the new Context based parrallel CPU

from collections import deque
from CIUcontroller import CIU  # <-- 1. IMPORT CIU CONTROLLER
# from memory import Memory
from memoryMMU import MMU 
from ucore  import Ucore

from ExecuterZ32A import _execute_cycleZ32 


# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class CPU:
    def __init__(self, cpu_id=0, memory=None):
        # self.memory = Memory(size=1024)
        # self.memory = Memory(Page0=1024, Private=512, Shared=1024, block_size=64)
        self.ID = cpu_id
        # Als er geen MMU wordt meegegeven, maken we een stand-alone instantie aan.
        # Als er wél een MMU wordt meegegeven (zoals door het Mainboard), gebruiken we die!
        self.memory = (
            memory
            if memory is not None
            else MMU(Page0=1024, Private=512, Shared=1024, block_size=64)
        )

        # --- CIU INTEGRATIE (ON-CHIP SILICON) ---
        self.ciu = CIU(self)  # <-- 2. KOOPPEL CIU AAN DEZE CPU

        # --- HARDWARE RESET STATE ---
        if self.ID == 0:
            self.fsm_state = "FETCH"  # Master start direct met de main-loop
        else:
            self.fsm_state = (
                "WAIT_FOR_WORK"  # Worker CPU's staan stil tot een CIU-signaal
            )

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

        # self.fsm_state = 'FETCH'             # FETCH, DECODE, EXECUTE
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
        self.io_bus = None

    def IO(self, io_controller):
        """De soldeerjumper methode die door het mainboard wordt aangeroepen"""
        self.io_bus = io_controller
        print("[CPU] Inmos-Z32: IO-Controller succesvol gekoppeld via interne bus.")


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


            # 2. CONTEXT SCHEDULER: Slimme dubbele tick bij FETCH
            
            active_running_contexts = [c for c in self.contexts if c.fsm_state in ('FETCH', 'DECODE', 'EXECUTE', 'RUNNING')]
            
            if active_running_contexts:
                # Veiligheidsmarge: mocht de lijst gekrompen zijn, zorg dat we nooit Out-of-Bounds gaan
                if self.current_context_index >= len(active_running_contexts):
                    self.current_context_index = 0
                    
                target_context = active_running_contexts[self.current_context_index]

                # # --- DEBUG PRINT: TOON EXECUTIE VAN CONTEXT OP CPU ---
                # print(
                #     f"\033[36m[CTX TICK CPU{self.ID}] Thread"
                #     f" #{self.current_context_index + 1}/{len(active_running_contexts)}"
                #     f" | State: {target_context.fsm_state:<7} | PC:"
                #     f" {target_context.PC:<3}\033[0m"
                # )

                
                # --- JOUW ELEGANTE LOGICA ---
                if target_context.fsm_state == 'FETCH':
                    # Run 2 ticks: Fetch pakt de instructie, de 2e tick voert DECODE direct uit!
                    self._execute_cycle(self, target_context)
                    self._execute_cycle(self, target_context)
                else:
                    # Run 1 tick: Voor DECODE, EXECUTE of hardware stalls
                    self._execute_cycle(self, target_context)
            
                # Schuif de Round Robin pointer netjes door
                self.current_context_index = (self.current_context_index + 1) % len(active_running_contexts)


            # Als de CPU in WAIT_FOR_WORK staat, doet de klok cyclus niks
            if self.fsm_state == "WAIT_FOR_WORK":
                return

            # 3. Voer DAARNA de huidige hoofd-CPU instructie uit
            self._execute_cycle(self, self)



    def is_completely_idle(self):
        """Controleert of de CPU volledig in rust is."""
        # 1. Als er nog actieve hardware-threads in de lijst zitten, zijn we NIET idle!
        if len(self.contexts) > 0:
            return False

        # 2. Als de hoofd-pijplijn nog draait (niet op HALT of WAIT_FOR_WORK), zijn we NIET idle!
        if self.fsm_state not in ["HALT", "WAIT_FOR_WORK"]:
            return False

        # 3. Als er nog minstens 1 micro-core aan het rekenen is, zijn we NIET idle!
        for core in self.cores:
            if core.coreStatus == "WORKING":
                return False

        # Pas als er GEEN contexts zijn, FSM in rust is én alle cores stilstaan, zijn we idle!
        return True

