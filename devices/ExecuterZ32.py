
# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class HardwareContext:
    def __init__(self, master_cpu, source_reg):
        """
        Representeert een hardware-thread (context) binnen de Inmos-Z32.
        Alloceert direct een vrije ucore vanuit de CPU free_cores pool.
        """
        self.memory = master_cpu.memory
        self.cores = master_cpu.cores
        
        # Elke context heeft een eigen, onafhankelijke registerfile
        self.registers = {i: None for i in range(10)}
        
        # 1. Haal de bronwaarde op uit de hoofd-CPU
        source_core_id = master_cpu.registers[source_reg]
        if source_core_id is None:
            raise RuntimeError(f"Hardware Fault: Register {source_reg} bevat geen geldige ucore-wijzer!")
        source_value = master_cpu.cores[source_core_id].value
        
        # 2. MATCH MET JOUW LOGICA: Check de pool en pop een vrije core
        if not master_cpu.free_cores:
            # Als er geen cores vrij zijn, zetten we de cpu_status op 0 (Fail)
            master_cpu.status = 0
            # We gooien een specifieke status zodat de CONTEXT-instructie weet dat hij moet stallen/afbreken
            raise RuntimeError("Hardware Stall: Geen vrije ucores beschikbaar in de pool!")
        
        else:
            # Succes! Pop de core direct uit de pool van de hoofd-CPU
            allocated_core_id = master_cpu.free_cores.popleft()
            master_cpu.status = 1  # Signaleer succes naar het cpu.status registe
        
            target_core = master_cpu.cores[allocated_core_id]
            
            # 3. Initialiseer de hardware-toestand van deze unieke core conform ucore.py
            target_core.value = source_value
            target_core.coreStatus = 'VALID'  # Correct voor de state van de core
            target_core.upc = 0               # Reset microcode program counter
            target_core.status = True         # De interne status-vlag (ALU/Branch conditie)
            
            # Maak de overige ALU-registers leeg voor de nieuwe thread
            target_core.work = 0              # W-register reset
            target_core.transfer = 0          # T-register reset
            
            # Eventuele hardware-latches voor het teken (+/-) resetten
            target_core.sign_v = 0
            target_core.sign_w = 0

            # Wijs deze exclusieve core toe aan het lokale register van de context
            self.registers[source_reg] = allocated_core_id

            # Context Executie Boekhouding
            self.fsm_state = 'FETCH'
            self.MIR = None
            self.PC = 0  # Wordt gevuld met het jumpadres door de CONTEXT instructie

            self.decoded_opcode = 0
            self.decoded_reg1 = 0
            self.decoded_arg2 = 0

            self.last_active_core = allocated_core_id
            self.last_test_core = None



def _execute_cycleZ32(master_cpu, target):
    """De CPU State Machine: 1 deeltaak per tick. 
    Werkt universeel voor zowel de hoofd-CPU als een HardwareContext (target)."""
    
    if target.fsm_state == 'FETCH':
        # FETCH leest altijd uit het gedeelde master-geheugen, maar gebruikt de PC van het target
        target.MIR = master_cpu.memory.memRead(target.PC)
        target.PC += 1
        target.fsm_state = 'DECODE'

    elif target.fsm_state == 'DECODE':
        if target.MIR == 0:               
            target.fsm_state = 'FETCH'
            return
            
        try:
            opcode = Op(target.MIR % 100)
        except ValueError:
            print(f"Hardware error: Unknown opcode {target.MIR % 100}")
            target.fsm_state = 'FETCH'
            return

        target.decoded_opcode = opcode
        payload = target.MIR // 100

        if opcode in FORMAT_ZERO:  
            target.decoded_reg1 = 0
            target.decoded_arg2 = 0
        elif opcode in FORMAT_ONE_ADDR:  
            target.decoded_reg1 = 0
            target.decoded_arg2 = payload       
        elif opcode in FORMAT_TWO_REG_REG:
            target.decoded_reg1 = payload % 10  
            target.decoded_arg2 = payload // 10 
        elif opcode in FORMAT_TWO_REG_VAL:
            target.decoded_reg1 = payload % 10  # Register
            target.decoded_arg2 = payload // 10 # Directe waarde of RAM-adres
        elif opcode in FORMAT_ONE_REG:
            target.decoded_reg1 = payload % 10
            target.decoded_arg2 = 0
        else:
            target.decoded_reg1 = payload % 10  
            target.decoded_arg2 = payload // 10 

        target.fsm_state = 'EXECUTE'

    elif target.fsm_state == 'EXECUTE':
        opcode = target.decoded_opcode
        reg1   = target.decoded_reg1
        arg2   = target.decoded_arg2

        # ==========================================
        #   CORE INSTRUCTIES (Vereisen een vrije core uit master_cpu)
        # ==========================================
        if opcode == Op.LDI:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            master_cpu.cores[core_id].transfer = arg2
            master_cpu.cores[core_id].dispatch('ldv')
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.LDM:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            mem_value = master_cpu.memory.memRead(arg2)
            
            master_cpu.cores[core_id].transfer = mem_value
            master_cpu.cores[core_id].dispatch('ldv') 
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.LDX:
            # LDX Rx mem_base -> Gebruikt target index-register R0
            index_core = target.registers[0]  
            
            if index_core is not None and master_cpu.cores[index_core].coreStatus == 'VALID':
                if not master_cpu.free_cores: return          # Fast Stall
                core_id = master_cpu.free_cores.popleft()     

                effective_addr = arg2 + master_cpu.cores[index_core].value
                ram_value = master_cpu.memory.memRead(effective_addr)
                
                master_cpu.cores[core_id].transfer = ram_value
                master_cpu.cores[core_id].dispatch('ldv') 
                target.registers[reg1] = core_id
                target.last_active_core = core_id
            else:
                return  # Stall

        elif opcode == Op.ADD:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('add', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            target.last_active_core = core_id         
            
        elif opcode == Op.MUL:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('slow_mul', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.INC:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]

            master_cpu.cores[core_id].dispatch('inc', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.DEC:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]

            master_cpu.cores[core_id].dispatch('dec', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.MOD:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('mod', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.XOR:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('xor_vw', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.SHIFTL:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('shftl', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.SM32_RND:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('sm32_rnd', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.ROTL32:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('rol32', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            target.last_active_core = core_id

        elif opcode == Op.TSTE:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2]
            
            master_cpu.cores[core_id].dispatch('cmpe', arg1=src1_core, arg2=src2_core)

            target.registers[reg1] = core_id
            target.last_active_core = core_id
            target.last_test_core = core_id  # Lokaal vastleggen voor target sprongen


        # ==========================================
        #   SYSTEM / FLOW CONTROL
        # ==========================================
        elif opcode == Op.HALT:
            target.fsm_state = 'HALT'
            return
        
        elif opcode == Op.STO:
            core_id = target.registers[reg1]
            
            if core_id is None:
                raise RuntimeError(
                    f"Hardware Fault: STO op PC={target.PC-1} (MIR={target.MIR}). "
                    f"Register {reg1} heeft geen actieve Core-ID!"
                )
            
            if master_cpu.cores[core_id].coreStatus != 'VALID':
                return # Stall
            
            value_to_store = master_cpu.cores[core_id].value
            master_cpu.memory.memWrite(value_to_store, adres=arg2)

        elif opcode == Op.STX:
            index_core = target.registers[0]         
            data_core = target.registers[reg1]       
            
            if (index_core is not None and master_cpu.cores[index_core].coreStatus == 'VALID' and
                data_core is not None and master_cpu.cores[data_core].coreStatus == 'VALID'):
                
                effective_addr = arg2 + master_cpu.cores[index_core].value
                val_to_store = master_cpu.cores[data_core].value
                master_cpu.memory.memWrite(val_to_store, adres=effective_addr)
            else:
                return  # Stall

        elif opcode == Op.JMP:
            target.PC = arg2

        elif opcode == Op.JMPT:
            if target.last_test_core is None:
                raise RuntimeError("Hardware Fault: JMPT zonder voorafgaande TSTE!")
            
            test_core = master_cpu.cores[target.last_test_core]
            if test_core.coreStatus == 'WORKING':
                target.fsm_state = 'EXECUTE'
                return
            
            if test_core.status == True:
                target.PC = arg2
            target.fsm_state = 'FETCH'

        elif opcode == Op.JMPF:
            if target.last_test_core is None:
                raise RuntimeError("Hardware Fault: JMPF zonder voorafgaande TSTE!")
            
            test_core = master_cpu.cores[target.last_test_core]
            if test_core.coreStatus == 'WORKING':
                target.fsm_state = 'EXECUTE'
                return
            
            if test_core.status == False:
                target.PC = arg2
            target.fsm_state = 'FETCH'

        # Zorg dat de standaardafhandeling de eigen FSM reset
        target.fsm_state = 'FETCH'















# def _execute_cycleZ32(self):
#         """De CPU State Machine: 1 deeltaak per tick."""
        
#         if self.fsm_state == 'FETCH':
#             self.MIR = self.memory.memRead(self.PC)
#             self.PC += 1
#             self.fsm_state = 'DECODE'

#         elif self.fsm_state == 'DECODE':
#             if self.MIR == 0:               
#                 self.fsm_state = 'FETCH'
#                 return
                
#             try:
#                 opcode = Op(self.MIR % 100)
#             except ValueError:
#                 print(f"Hardware error: Unknown opcode {self.MIR % 100}")
#                 self.fsm_state = 'FETCH'
#                 return

#             self.decoded_opcode = opcode
#             payload = self.MIR // 100

#             if opcode in FORMAT_ZERO:  
#                 self.decoded_reg1 = 0
#                 self.decoded_arg2 = 0
#             elif opcode in FORMAT_ONE_ADDR:  
#                 self.decoded_reg1 = 0
#                 self.decoded_arg2 = payload       
#             elif opcode in FORMAT_TWO_REG_REG:
#                 self.decoded_reg1 = payload % 10  
#                 self.decoded_arg2 = payload // 10 
#             elif opcode in FORMAT_TWO_REG_VAL:
#                 self.decoded_reg1 = payload % 10  # Register
#                 self.decoded_arg2 = payload // 10 # Directe waarde of RAM-adres
#             elif opcode in FORMAT_ONE_REG:
#                 self.decoded_reg1 = payload % 10
#                 self.decoded_arg2 = 0
#             else:
#                 self.decoded_reg1 = payload % 10  
#                 self.decoded_arg2 = payload // 10 

#             self.fsm_state = 'EXECUTE'

#         elif self.fsm_state == 'EXECUTE':
#             opcode = self.decoded_opcode
#             reg1   = self.decoded_reg1
#             arg2   = self.decoded_arg2

#             # ==========================================
#             #   CORE INSTRUCTIES (Vereisen een vrije core)
#             # ==========================================
#             if opcode == Op.LDI:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 self.cores[core_id].transfer = arg2
#                 self.cores[core_id].dispatch('ldv')
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.LDM:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 # FIX: Haal de waarde écht uit het RAM-geheugen (arg2 = 20)
#                 mem_value = self.memory.memRead(arg2)
                
#                 self.cores[core_id].transfer = mem_value
#                 self.cores[core_id].dispatch('ldv') # Laad de waarde in de core
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.LDX:
                
#                 # LDX Rx mem_base -> Laad in Rx de waarde vanaf RAM-adres (mem_base + R0)
#                 # R0 (index 0) is ons vaste index-register 'I'
#                 index_core = self.registers[0]  # Haal de core op die gekoppeld is aan R0 (I)
                
#                 if index_core is not None and self.cores[index_core].coreStatus == 'VALID':
#                     if not self.free_cores: return          #  Fast Stall when there is no free ucore
#                     core_id = self.free_cores.popleft()     #  Get the ucore 

#                     # Bereken het effectieve adres: mem_base (arg2) + de waarde van I
#                     effective_addr = arg2 + self.cores[index_core].value
#                     ram_value = self.memory.memRead(effective_addr)
                    
#                     self.cores[core_id].transfer = ram_value
#                     self.cores[core_id].dispatch('ldv') # Laad de waarde in de core
#                     self.registers[reg1] = core_id
#                     self.last_active_core = core_id
#                 else:
#                     return  # Stall de CPU als de waarde in index-register I nog niet VALID is
        

#             elif opcode == Op.ADD:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 src1_core = self.registers[reg1]
#                 src2_core = self.registers[arg2] 
                
#                 self.cores[core_id].dispatch('add', arg1=src1_core, arg2=src2_core)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id         
                
#             elif opcode == Op.MUL:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 src1_core = self.registers[reg1]
#                 src2_core = self.registers[arg2] 
                
#                 self.cores[core_id].dispatch('slow_mul', arg1=src1_core, arg2=src2_core)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.INC:
#                 if not self.free_cores: return # stall
#                 core_id = self.free_cores.popleft()

#                 src1_core = self.registers[reg1]

#                 self.cores[core_id].dispatch('inc', arg1=src1_core, arg2=None)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.DEC:
#                 if not self.free_cores: return # stall
#                 core_id = self.free_cores.popleft()

#                 src1_core = self.registers[reg1]

#                 self.cores[core_id].dispatch('dec', arg1=src1_core, arg2=None)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.MOD:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 src1_core = self.registers[reg1]
#                 src2_core = self.registers[arg2] 
                
#                 self.cores[core_id].dispatch('mod', arg1=src1_core, arg2=src2_core)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.XOR:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 src1_core = self.registers[reg1]
#                 src2_core = self.registers[arg2] 
                
#                 self.cores[core_id].dispatch('xor_vw', arg1=src1_core, arg2=src2_core)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.SHIFTL:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()

#                 src1_core = self.registers[reg1]
#                 self.cores[core_id].transfer = arg2

#                 self.cores[core_id].dispatch('shftl', arg1=src1_core, arg2=None)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.SM32_RND:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()

#                 src1_core = self.registers[reg1]
#                 self.cores[core_id].transfer = arg2

#                 self.cores[core_id].dispatch('sm32_rnd', arg1=src1_core, arg2=None)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

            

#             elif opcode == Op.ROTL32:
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()

#                 src1_core = self.registers[reg1]
#                 self.cores[core_id].transfer = arg2

#                 # Start de 'rol32' microcode keten
#                 self.cores[core_id].dispatch('rol32', arg1=src1_core, arg2=None)
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id

#             elif opcode == Op.TSTE:
#                 # Test op Gelijkheid (bijv: tste A B)
#                 if not self.free_cores: return # Stall
#                 core_id = self.free_cores.popleft()
                
#                 src1_core = self.registers[reg1]
#                 src2_core = self.registers[arg2]
                
#                 # Start de core met de microcode 'cmpe' uit ucore.py
#                 self.cores[core_id].dispatch('cmpe', arg1=src1_core, arg2=src2_core)

                
#                 # Update de registers én registreer dit als de laatste test-core!
#                 self.registers[reg1] = core_id
#                 self.last_active_core = core_id
#                 self.last_test_core = core_id  # <--- HIER leggen we de 'booleaanse waarheid' vast!


#             # ==========================================
#             #   SYSTEM / FLOW CONTROL
#             # ==========================================
#             elif opcode == Op.HALT:
#                 # We zetten een vlaggetje of stoppen de CPU-state machine
#                 # Zodat main.py weet dat we klaar zijn.
#                 self.fsm_state = 'HALT'
#                 return
            
#             elif opcode == Op.STO:
#                 # STO reg1 arg2 -> Sla de waarde van reg1 op in memory[arg2]
#                 core_id = self.registers[reg1]
                
#                 # HARDWARE CHECK: Als het register nog None is (nooit toegewezen), gooien we een crash
#                 if core_id is None:
#                     raise RuntimeError(
#                         f"Hardware Fault: STO aangeroepen op PC={self.PC-1} "
#                         f"(MIR={self.MIR}) waarbij Register {reg1} wordt aangesproken, "
#                         f"maar dit register heeft nog geen actieve Core-ID toegewezen gekregen!"
#                     )
                
#                 # 1. HARDWARE STALL: Wacht tot de betreffende core klaar is met rekenen!
#                 if self.cores[core_id].coreStatus != 'VALID':
#                     return # Blijf in EXECUTE-state (stall) tot de core-data stabiel is.
                
#                 # 2. Haal de waarde rechtstreeks uit de stabiele core
#                 value_to_store = self.cores[core_id].value
                
#                 # 3. Schrijf de waarde direct weg naar het RAM-geheugen
#                 self.memory.memWrite(value_to_store, adres=arg2)

#             elif opcode == Op.STX:
#                 # STX Rx mem_base -> Sla de waarde van Rx op op RAM-adres (mem_base + R0)
#                 index_core = self.registers[0]         # R0 is ons index-register I
#                 data_core = self.registers[reg1]       # De core gekoppeld aan Rx die we willen opslaan
                
#                 # We kunnen pas schrijven als BEIDE cores VALID zijn!
#                 if (index_core is not None and self.cores[index_core].coreStatus == 'VALID' and
#                     data_core is not None and self.cores[data_core].coreStatus == 'VALID'):
                    
#                     # Bereken het effectieve adres: mem_base (arg2) + de waarde van I
#                     effective_addr = arg2 + self.cores[index_core].value
#                     val_to_store = self.cores[data_core].value
                    
#                     # Schrijf het direct weg naar het RAM-geheugen
#                     # self.memory.memWrite(effective_addr, val_to_store)
#                     self.memory.memWrite(val_to_store, adres=effective_addr)
#                 else:
#                     return  # Stall de CPU als I of Rx nog niet klaar is met rekenen

#             elif opcode == Op.JMP:
#                 self.PC = arg2

        
#             elif opcode == Op.JMPT:
#                 if self.last_test_core is None:
#                     raise RuntimeError("Hardware Fault: JMPT zonder voorafgaande TSTE!")
                
#                 test_core = self.cores[self.last_test_core]
                
#                 # STAP 1: De Stall-barrière
#                 # Is de ucore nog bezig? Dwing de EXECUTE-state en stop de tick (Stall)
#                 if test_core.coreStatus == 'WORKING':
#                     self.fsm_state = 'EXECUTE'
#                     return
                
#                 # STAP 2: De Ontsnapping / Uitvoering
#                 # Als we hier komen is de core gegarandeerd VALID!
#                 if test_core.status == True:
#                     self.PC = arg2
                
#                 # De instructie is afgehandeld, we mogen weer fetchen
#                 self.fsm_state = 'FETCH'


#             elif opcode == Op.JMPF:
#                 if self.last_test_core is None:
#                     raise RuntimeError("Hardware Fault: JMPF zonder voorafgaande TSTE!")
                
#                 test_core = self.cores[self.last_test_core]
                
#                 # STAP 1: De Stall-barrière
#                 # Is de ucore nog bezig? Dwing de EXECUTE-state en stop de tick (Stall)
#                 if test_core.coreStatus == 'WORKING':
#                     self.fsm_state = 'EXECUTE'
#                     return
                
#                 # STAP 2: De Ontsnapping / Uitvoering
#                 # Als we hier komen is de core gegarandeerd VALID!
#                 if test_core.status == False:
#                     self.PC = arg2
                
#                 # De instructie is afgehandeld, we mogen weer fetchen
#                 self.fsm_state = 'FETCH'

#             self.fsm_state = 'FETCH'







""" some example assemblycode 
ldi A 20        ; Laad A met 20
ldm B 20        ; Laad B met de waarde van $mem (adres 20)
add A B         ; tel A en B bij elkaar op
halt
"""