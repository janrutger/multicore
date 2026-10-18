# Inmos_Z32A.py 
# Start of the new Context based parrallel CPU

from collections import deque
import time
# from CIUcontrollerV2r2 import CIU  # <-- 1. IMPORT CIU CONTROLLER
from CIUbusV2r1 import CIU
# from memory import Memory
from memoryMMU import MMU 
from ucore  import Ucore

from ExecuterZ32AV2r2 import _execute_cycleZ32 


# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class CPU:
    def __init__(self, cpu_id=0, memory=None):
        ## Hardeware countertimers
        self.time_ucore = 0.0      # Pure uCore microsteps
        self.time_gc = 0.0         # Garbage collection ("wezen check")
        self.time_context = 0.0    # RCONTEXT thread scheduler
        self.time_main = 0.0       # Hoofd-CPU pipeline execution
        self.max_contexts = 0      # Maimaal aantal gelijktijdige contexten

        self.ID = cpu_id
        self.parent_id = cpu_id

        # self.memory = Memory(size=1024)
        # self.memory = Memory(Page0=1024, Private=512, Shared=1024, block_size=64)
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

        # self.last_active_core = None      # Buitengebruik sind 20sept26
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


    
    # def tick(self):
    #     """Voert één volledige kloksnelheid-cyclus uit voor het hele systeem."""
        
    #     # ==========================================================
    #     # 1. uCORE MATRIX TICKS (Eén meting voor álle cores samen)
    #     # ==========================================================
    #     t0 = time.perf_counter()
    #     for core_id, core in enumerate(self.cores):
    #         core.tick()

    #         # --- STAP A: Geef de reeds IDLE cores terug aan de wachtrij ---
    #         if core.coreStatus == 'IDLE' and core_id not in self.free_cores:
    #             self.free_cores.append(core_id)
                
    #     t1 = time.perf_counter()
    #     self.time_ucore += (t1 - t0)

    #     # ==========================================================
    #     # 2. GARBAGE COLLECTION / WEZEN-CHECK (Eén meting voor de hele check)
    #     # ==========================================================
    #     t0 = time.perf_counter()
    #     for core_id, core in enumerate(self.cores):
    #         if core.coreStatus == 'VALID':
    #             # 1. Check Master CPU registers
    #             in_master_register = any(reg_id == core_id for reg_id in self.registers.values())
                
    #             # 2. Check ALLE threads die nog in het systeem zitten (ongeacht FSM status!)
    #             in_thread_register = False
    #             for ctx in self.contexts:
    #                 if any(reg_id == core_id for reg_id in ctx.registers.values()):
    #                     in_thread_register = True
    #                     break
                        
    #             is_test_core = (self.last_test_core == core_id)
                
    #             # 3. Check of er een WORKING core is die deze core nodig heeft
    #             wordt_nog_bezocht = False
    #             for andere_core in self.cores:
    #                 if andere_core.coreStatus == 'WORKING':
    #                     if andere_core.arg1 == core_id or andere_core.arg2 == core_id:
    #                         wordt_nog_bezocht = True
    #                         break
                
    #             # Alleen slopen als hij énkel door helemaal niemand meer geclaimd wordt
    #             if not in_master_register and not in_thread_register and not is_test_core and not wordt_nog_bezocht:
    #                 core.coreStatus = 'IDLE'
                    
    #     t1 = time.perf_counter()
    #     self.time_gc += (t1 - t0)
    def tick(self):
        """Voert één volledige kloksnelheid-cyclus uit voor het hele systeem."""
        
        # Lokale referenties voor snelheid (vermijdt 'self.' lookup in loops)
        current_cores = self.cores
        current_free_cores = self.free_cores

        # ==========================================================
        # 1. uCORE MATRIX TICKS
        # ==========================================================
        t0 = time.perf_counter()
        
        # Gebruik bereik in plaats van enumerate als we core_id niet direct nodig hebben
        # of als we lokale refs gebruiken.
        for core in current_cores:
            core.tick()
                
        self.time_ucore += (time.perf_counter() - t0)

        # ==========================================================
        # 2. GARBAGE COLLECTION / WEZEN-CHECK (Geoptimaliseerd)
        # ==========================================================
        t0 = time.perf_counter()
        
        # --- PRE-BEREKENING: Bouw een set van álle actieve referenties ---
        # Lookups in een set zijn O(1). Dit is de sleutel tot de versnelling.
        claimed_cores = set()
        
        # 1. Verzamel Master CPU registers
        for reg_id in self.registers.values():
            if reg_id is not None:
                claimed_cores.add(reg_id)
        
        # 2. Verzamel referenties uit ALLE actieve threads
        for ctx in self.contexts:
            # Platgeslagen loop is vaak sneller dan set(ctx.registers.values()) onder PyPy
            for reg_id in ctx.registers.values():
                if reg_id is not None:
                    claimed_cores.add(reg_id)
        
        # 3. Voeg de speciale test_core toe
        if self.last_test_core is not None:
            claimed_cores.add(self.last_test_core)
            
        # 4. Verzamel dependencies van WORKING cores
        for core in current_cores:
            if core.coreStatus == 'WORKING':
                if core.arg1 is not None:
                    claimed_cores.add(core.arg1)
                if core.arg2 is not None:
                    claimed_cores.add(core.arg2)

        # --- HOOFD GC LOOP: Scann de cores ---
        for core_id, core in enumerate(current_cores):
            status = core.coreStatus
            
            # --- Geïntegreerde Stap A: IDLE cores teruggeven ---
            if status == 'IDLE':
                # Gebruikmakend van het feit dat free_cores nu waarschijnlijk een set of 
                # efficiënte queue is. Als het een set is, is 'in' O(1).
                if core_id not in current_free_cores:
                    current_free_cores.append(core_id)
                continue # Direct door naar de volgende core

            # --- Stap B: Wezen-check voor VALID cores ---
            if status == 'VALID':
                # O(1) lookup in de pre-berekende set
                if core_id not in claimed_cores:
                    core.coreStatus = 'IDLE'
                    # Optioneel: direct toevoegen aan free_cores, 
                    # maar dat gebeurt de volgende tick via Stap A ook.
                    # current_free_cores.append(core_id)
                    
        self.time_gc += (time.perf_counter() - t0)

        # ==========================================================
        # 3. CONTEXT SCHEDULER (RCONTEXT THREADS)
        # ==========================================================
        # t0 = time.perf_counter()
        active_running_contexts = [c for c in self.contexts if c.fsm_state in ('FETCH', 'DECODE', 'EXECUTE', 'RUNNING')]

        # # --- HIER BIJHOUDEN VAN DE CONCURRENTIE-PIEK ---
        # if len(active_running_contexts) > self.max_contexts:
        #     self.max_contexts = len(active_running_contexts)
        
        if active_running_contexts:
            t0 = time.perf_counter()
            # --- HIER BIJHOUDEN VAN DE CONCURRENTIE-PIEK ---
            if len(active_running_contexts) > self.max_contexts:
                self.max_contexts = len(active_running_contexts)

            if self.current_context_index >= len(active_running_contexts):
                self.current_context_index = 0
                
            target_context = active_running_contexts[self.current_context_index]

            if target_context.fsm_state == 'FETCH':
                self._execute_cycle(self, target_context)
                self._execute_cycle(self, target_context)
            else:
                self._execute_cycle(self, target_context)
        
            self.current_context_index = (self.current_context_index + 1) % len(active_running_contexts)
            
        # t1 = time.perf_counter()
        # self.time_context += (t1 - t0)
            self.time_context += (time.perf_counter() - t0)

        # ==========================================================
        # 4. HOOFD-CPU PIPELINE
        # ==========================================================
        if self.fsm_state == "WAIT_FOR_WORK":
            return

        t0 = time.perf_counter()
        self._execute_cycle(self, self)
        t1 = time.perf_counter()
        self.time_main += (t1 - t0)



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

