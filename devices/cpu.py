# cpu.py
from collections import deque
from memory import Memory
from ucore  import Ucore

# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class CPU:
    def __init__(self):
        self.memory = Memory(size=1024)

        # Stap 1: Maak alle cores onafhankelijk aan
        self.cores = [Ucore() for _ in range(16)]

        # Stap 2: Koppel ze aan de matrix-omgeving (de lijst zelf)
        for core in self.cores:
            core.initCoreMatrix(self.cores)

        self.last_active_core = None
        self.last_test_core   = None        # Slaat specifiek de Core-ID op van de LAATSTE test/vergelijking


        # register setup
        self.PC  = 0                           # Program counter
        self.SP  = self.memory.memSize() - 1   # Stackpointer

        self.cpu_state = 'FETCH'             # FETCH, DECODE, EXECUTE
        self.MIR       = None                # Memory Instruction Register (onze huidige integer)

        # Tijdelijk gedecodede variabelen die we bewaren tussen de ticks door
        self.decoded_opcode = 0
        self.decoded_reg1   = 0
        self.decoded_arg2   = 0

        # Registers bevatten de Core-ID die de waarde vertegenwoordigt
        self.registers = {i: None for i in range(10)}      

        # --- DYNAMISCH CORE BEHEER ---
        # We stoppen alle Core ID's (0 t/m 15) in de vrije wachtrij
        self.free_cores = deque(range(16))


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
                        # core.value = 0
                        # core.work = 0
                        # core.transfer = 0
                        # core.upc = 0

            # 2. Voer DAARNA de huidige hoofd-CPU instructie uit
            self._execute_cycle()


    def _execute_cycle(self):
        """De CPU State Machine: 1 deeltaak per tick."""
        
        if self.cpu_state == 'FETCH':
            self.MIR = self.memory.memRead(self.PC)
            self.PC += 1
            self.cpu_state = 'DECODE'

        elif self.cpu_state == 'DECODE':
            if self.MIR == 0:               
                self.cpu_state = 'FETCH'
                return
                
            try:
                opcode = Op(self.MIR % 100)
            except ValueError:
                print(f"Hardware error: Unknown opcode {self.MIR % 100}")
                self.cpu_state = 'FETCH'
                return

            self.decoded_opcode = opcode
            payload = self.MIR // 100

            if opcode in FORMAT_ZERO:  
                self.decoded_reg1 = 0
                self.decoded_arg2 = 0
            elif opcode in FORMAT_ONE_ADDR:  
                self.decoded_reg1 = 0
                self.decoded_arg2 = payload       
            elif opcode in FORMAT_TWO_REG_REG:
                self.decoded_reg1 = payload % 10  
                self.decoded_arg2 = payload // 10 
            elif opcode in FORMAT_TWO_REG_VAL:
                self.decoded_reg1 = payload % 10  # Register
                self.decoded_arg2 = payload // 10 # Directe waarde of RAM-adres
            elif opcode in FORMAT_ONE_REG:
                self.decoded_reg1 = payload % 10
                self.decoded_arg2 = 0
            else:
                self.decoded_reg1 = payload % 10  
                self.decoded_arg2 = payload // 10 

            self.cpu_state = 'EXECUTE'

        elif self.cpu_state == 'EXECUTE':
            opcode = self.decoded_opcode
            reg1   = self.decoded_reg1
            arg2   = self.decoded_arg2

            # ==========================================
            #   CORE INSTRUCTIES (Vereisen een vrije core)
            # ==========================================
            if opcode == Op.LDI:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                self.cores[core_id].transfer = arg2
                self.cores[core_id].dispatch('ldv')
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.LDM:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                # FIX: Haal de waarde écht uit het RAM-geheugen (arg2 = 20)
                mem_value = self.memory.memRead(arg2)
                
                self.cores[core_id].transfer = mem_value
                self.cores[core_id].dispatch('ldv') # Laad de waarde in de core
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.LDX:
                
                # LDX Rx mem_base -> Laad in Rx de waarde vanaf RAM-adres (mem_base + R0)
                # R0 (index 0) is ons vaste index-register 'I'
                index_core = self.registers[0]  # Haal de core op die gekoppeld is aan R0 (I)
                
                if index_core is not None and self.cores[index_core].coreStatus == 'VALID':
                    if not self.free_cores: return          #  Fast Stall when there is no free ucore
                    core_id = self.free_cores.popleft()     #  Get the ucore 

                    # Bereken het effectieve adres: mem_base (arg2) + de waarde van I
                    effective_addr = arg2 + self.cores[index_core].value
                    ram_value = self.memory.memRead(effective_addr)
                    
                    self.cores[core_id].transfer = ram_value
                    self.cores[core_id].dispatch('ldv') # Laad de waarde in de core
                    self.registers[reg1] = core_id
                    self.last_active_core = core_id
                else:
                    return  # Stall de CPU als de waarde in index-register I nog niet VALID is
        

            elif opcode == Op.ADD:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                src1_core = self.registers[reg1]
                src2_core = self.registers[arg2] 
                
                self.cores[core_id].dispatch('add', arg1=src1_core, arg2=src2_core)
                self.registers[reg1] = core_id
                self.last_active_core = core_id         
                
            elif opcode == Op.MUL:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                src1_core = self.registers[reg1]
                src2_core = self.registers[arg2] 
                
                self.cores[core_id].dispatch('slow_mul', arg1=src1_core, arg2=src2_core)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.INC:
                if not self.free_cores: return # stall
                core_id = self.free_cores.popleft()

                src1_core = self.registers[reg1]

                self.cores[core_id].dispatch('inc', arg1=src1_core, arg2=None)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.DEC:
                if not self.free_cores: return # stall
                core_id = self.free_cores.popleft()

                src1_core = self.registers[reg1]

                self.cores[core_id].dispatch('dec', arg1=src1_core, arg2=None)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.MOD:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                src1_core = self.registers[reg1]
                src2_core = self.registers[arg2] 
                
                self.cores[core_id].dispatch('mod', arg1=src1_core, arg2=src2_core)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.XOR:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                src1_core = self.registers[reg1]
                src2_core = self.registers[arg2] 
                
                self.cores[core_id].dispatch('xor_vw', arg1=src1_core, arg2=src2_core)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.SHIFTL:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()

                src1_core = self.registers[reg1]
                self.cores[core_id].transfer = arg2

                self.cores[core_id].dispatch('shftl', arg1=src1_core, arg2=None)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.SM32_RND:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()

                src1_core = self.registers[reg1]
                self.cores[core_id].transfer = arg2

                self.cores[core_id].dispatch('sm32_rnd', arg1=src1_core, arg2=None)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            

            elif opcode == Op.ROTL32:
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()

                src1_core = self.registers[reg1]
                self.cores[core_id].transfer = arg2

                # Start de 'rol32' microcode keten
                self.cores[core_id].dispatch('rol32', arg1=src1_core, arg2=None)
                self.registers[reg1] = core_id
                self.last_active_core = core_id

            elif opcode == Op.TSTE:
                # NIEUW: Test op Gelijkheid (bijv: tste A B)
                if not self.free_cores: return # Stall
                core_id = self.free_cores.popleft()
                
                src1_core = self.registers[reg1]
                src2_core = self.registers[arg2]
                
                # Start de core met de microcode 'cmpe' uit ucore.py
                self.cores[core_id].dispatch('cmpe', arg1=src1_core, arg2=src2_core)

                
                # Update de registers én registreer dit als de laatste test-core!
                self.registers[reg1] = core_id
                self.last_active_core = core_id
                self.last_test_core = core_id  # <--- HIER leggen we de 'booleaanse waarheid' vast!


            # ==========================================
            #   SYSTEM / FLOW CONTROL
            # ==========================================
            elif opcode == Op.HALT:
                # We zetten een vlaggetje of stoppen de CPU-state machine
                # Zodat main.py weet dat we klaar zijn.
                self.cpu_state = 'HALT'
                return
            
            elif opcode == Op.STO:
                # STO reg1 arg2 -> Sla de waarde van reg1 op in memory[arg2]
                core_id = self.registers[reg1]
                
                # HARDWARE CHECK: Als het register nog None is (nooit toegewezen), gooien we een crash
                if core_id is None:
                    raise RuntimeError(
                        f"Hardware Fault: STO aangeroepen op PC={self.PC-1} "
                        f"(MIR={self.MIR}) waarbij Register {reg1} wordt aangesproken, "
                        f"maar dit register heeft nog geen actieve Core-ID toegewezen gekregen!"
                    )
                
                # 1. HARDWARE STALL: Wacht tot de betreffende core klaar is met rekenen!
                if self.cores[core_id].coreStatus != 'VALID':
                    return # Blijf in EXECUTE-state (stall) tot de core-data stabiel is.
                
                # 2. Haal de waarde rechtstreeks uit de stabiele core
                value_to_store = self.cores[core_id].value
                
                # 3. Schrijf de waarde direct weg naar het RAM-geheugen
                self.memory.memWrite(value_to_store, adres=arg2)

            elif opcode == Op.STX:
                # STX Rx mem_base -> Sla de waarde van Rx op op RAM-adres (mem_base + R0)
                index_core = self.registers[0]         # R0 is ons index-register I
                data_core = self.registers[reg1]       # De core gekoppeld aan Rx die we willen opslaan
                
                # We kunnen pas schrijven als BEIDE cores VALID zijn!
                if (index_core is not None and self.cores[index_core].coreStatus == 'VALID' and
                    data_core is not None and self.cores[data_core].coreStatus == 'VALID'):
                    
                    # Bereken het effectieve adres: mem_base (arg2) + de waarde van I
                    effective_addr = arg2 + self.cores[index_core].value
                    val_to_store = self.cores[data_core].value
                    
                    # Schrijf het direct weg naar het RAM-geheugen
                    # self.memory.memWrite(effective_addr, val_to_store)
                    self.memory.memWrite(val_to_store, adres=effective_addr)
                else:
                    return  # Stall de CPU als I of Rx nog niet klaar is met rekenen

            elif opcode == Op.JMP:
                self.PC = arg2

            # elif opcode == Op.JMPT:
            #     # GEWIJZIGD: We kijken nu naar last_test_core in plaats van last_active_core!
            #     if self.last_test_core is not None:
            #         # Wacht tot de specifieke test-core op VALID springt
            #         if self.cores[self.last_test_core].coreStatus == 'VALID':
            #             if self.cores[self.last_test_core].status == True:
            #                 self.PC = arg2
            #             # Als de status False is, springen we niet en gaan we gewoon naar de volgende FETCH
            #         else:
            #             return # Stall! De test-core is nog bezig, bevries de CPU voor deze tick.
            #     else:
            #         # FIX: Geen silent error meer, maar een keiharde hardware crash!
            #         raise RuntimeError(
            #             f"Hardware Fault: JMPT aangeroepen op PC={self.PC-1} "
            #             f"(MIR={self.MIR}) zonder dat er vooraf een test-instructie "
            #             f"(zoals TSTE) is uitgevoerd!"
            #         )
            elif opcode == Op.JMPT:
                if self.last_test_core is None:
                    raise RuntimeError("Hardware Fault: JMPT zonder voorafgaande TSTE!")
                
                test_core = self.cores[self.last_test_core]
                
                # STAP 1: De Stall-barrière
                # Is de ucore nog bezig? Dwing de EXECUTE-state en stop de tick (Stall)
                if test_core.coreStatus == 'WORKING':
                    self.cpu_state = 'EXECUTE'
                    return
                
                # STAP 2: De Ontsnapping / Uitvoering
                # Als we hier komen is de core gegarandeerd VALID!
                if test_core.status == True:
                    self.PC = arg2
                
                # De instructie is afgehandeld, we mogen weer fetchen
                self.cpu_state = 'FETCH'

            # elif opcode == Op.JMPF:
            #     # GEWIJZIGD: Idem voor Jump if False
            #     if self.last_test_core is not None:
            #         if self.cores[self.last_test_core].coreStatus == 'VALID':
            #             if self.cores[self.last_test_core].status == False:
            #                 self.PC = arg2
            #         else:
            #             return # Stall
            #     else:
            #         # FIX: Geen silent error meer, maar een keiharde hardware crash!
            #         raise RuntimeError(
            #             f"Hardware Fault: JMPF aangeroepen op PC={self.PC-1} "
            #             f"(MIR={self.MIR}) zonder dat er vooraf een test-instructie "
            #             f"(zoals TSTE) is uitgevoerd!"
            #         )

            elif opcode == Op.JMPF:
                if self.last_test_core is None:
                    raise RuntimeError("Hardware Fault: JMPF zonder voorafgaande TSTE!")
                
                test_core = self.cores[self.last_test_core]
                
                # STAP 1: De Stall-barrière
                # Is de ucore nog bezig? Dwing de EXECUTE-state en stop de tick (Stall)
                if test_core.coreStatus == 'WORKING':
                    self.cpu_state = 'EXECUTE'
                    return
                
                # STAP 2: De Ontsnapping / Uitvoering
                # Als we hier komen is de core gegarandeerd VALID!
                if test_core.status == False:
                    self.PC = arg2
                
                # De instructie is afgehandeld, we mogen weer fetchen
                self.cpu_state = 'FETCH'

            self.cpu_state = 'FETCH'


    def is_completely_idle(self):
        """Controleert of de CPU op HALT staat én alle cores klaar zijn met rekenen."""
        if self.cpu_state != 'HALT':
            return False
            
        # Check of er nog ergens een core aan het werk is
        for core in self.cores:
            if core.coreStatus == 'WORKING':
                return False
                
        # Als de CPU op HALT staat en geen enkele core is WORKING, zijn we klaar!
        return True





""" some example assemblycode 
ldi A 20        ; Laad A met 20
ldm B 20        ; Laad B met de waarde van $mem (adres 20)
add A B         ; tel A en B bij elkaar op
halt
"""