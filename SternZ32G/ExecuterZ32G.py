
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
            # raise RuntimeError("Hardware Stall: Geen vrije ucores beschikbaar in de pool!")
        
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

        elif opcode == Op.LD:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
        
            master_cpu.cores[core_id].dispatch('ld', arg1=src1_core, arg2=src2_core) 
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

        elif opcode == Op.SUCCES:
            if master_cpu.status == 1:
                master_cpu.PC = arg2
            master_cpu.fsm_state = 'FETCH'

        elif opcode == Op.FAIL:
            if master_cpu.status == 0:
                master_cpu.PC = arg2
                master_cpu.status = 1
            master_cpu.fsm_state = 'FETCH'

        elif opcode == Op.SYNC:
            # Check of er nog asynchrone contexts in de matrix draaien
            if len(master_cpu.contexts) > 0:
                # Er is nog activiteit! Spring direct naar het opgegeven adres
                target.PC = arg2  # arg2 bevat het label-adres uit de assembly
                master_cpu.status = 0
            else:
                # De matrix is volledig stilgevallen en leeg. Succes!
                master_cpu.status = 1
                target.fsm_state = 'FETCH' # Stroom geruisloos door naar de volgende regel


        elif opcode == Op.CONTEXT:
            # Alleen de hoofd-CPU (master) mag threads (contexts) spawnen
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context probeerde zelf een CONTEXT te spawnen!")
                
            # 1. HARDWARE HIGH-WATERMARK CHECK: 
            # We hebben maximaal 10 cores per context nodig, om deadlocks te voorkomen een highwater mark van 10!
            if len(master_cpu.free_cores) < 10:
                master_cpu.status = 0          # Signaleer FAIL naar de CPU status
                target.fsm_state = 'FETCH'     # NIET STALLEN! Ga direct naar de volgende instructie (FAIL)
                return                         # Breek de CONTEXT-allocatie veilig af
            
            # 2. Allocatie is gegarandeerd succesvol! Maak nu pas de hardware context aan
            nieuwe_ctx = HardwareContext(master_cpu, reg1)
                
            # 3. Configureer de startparameters van de thread
            nieuwe_ctx.PC = arg2            # Dit wordt het startadres (bijv. 11)
            nieuwe_ctx.fsm_state = 'FETCH'  # Activeer de thread direct voor de scheduler
            
            # 4. Voeg hem toe aan de actieve contexts lijst
            master_cpu.contexts.append(nieuwe_ctx)
            target.fsm_state = 'FETCH'

            # # === NIEUWE DEBUG PRINT REGEL ===
            # ctx_id = len(master_cpu.contexts) - 1
            # cores_over = len(master_cpu.free_cores)
            # # \033[38;2;0;255;50m dwingt exact die giftige, felle 'blood green' af
            # print(f"\033[38;2;0;255;50m[SPAWN] 🚀 Context #{ctx_id:02d} aangemaakt | Matrix pool: {cores_over} cores vrij\033[0m")
            # # =================================

        elif opcode == Op.CLOSE:
            if target == master_cpu:
                raise RuntimeError("Hardware Fault: De master-CPU mag CLOSE niet aanroepen!")
            
            # We lopen door de registers van de thread
            for reg_val in target.registers.values():
                if reg_val is not None:  # Dit is een Core-ID wijzer naar ons (eind)resultaat
                    assigned_core = master_cpu.cores[reg_val]
                    
                    # Een core is pas bruikbaar voor de Master als de dataflow-keten 
                    # volledig is afgerond en de core de status 'VALID' heeft bereikt.
                    # Als hij nog 'WORKING' is, óf nog moet beginnen ('IDLE' maar onderdeel van een keten),
                    # moeten we de thread laten stallen.
                    if assigned_core.coreStatus == 'WORKING':
                        # De keten is nog niet klaar! Dwing de thread om te wachten.
                        target.fsm_state = 'EXECUTE'
                        return 

            # Pas als álle cores in de registers van de thread de status 'VALID' hebben,
            # is de berekening gegarandeerd voltooid en kan de Master veilig JOINEN.
            target.fsm_state = 'DONE'
            return

        elif opcode == Op.RETURN:
            if target == master_cpu:
                raise RuntimeError("Hardware Fault: De master-CPU mag CLOSE niet aanroepen!")
            
            # We lopen door de registers van de context en contoleren of alles IDLE (context is echt klaar) is
            for reg_val in target.registers.values():
                if reg_val is not None:  # Dit is een Core-ID wijzer naar ons (eind)resultaat
                    assigned_core = master_cpu.cores[reg_val]
                    if assigned_core.coreStatus == 'WORKING':
                        # De keten is nog niet klaar! Dwing de thread om te wachten.
                        target.fsm_state = 'EXECUTE'
                        return 
            # Pas als álle cores in de registers van de thread de status 'VALID' hebben,
            # is de berekening gegarandeerd voltooid en kan de Master veilig JOINEN.
            target.fsm_state = 'DONE'


            # SCHOONMAAKWERK: Zet alle overige uCores van deze thread-context op IDLE
            for reg_idx, core_id in target.registers.items():
                if core_id is not None:
                    if reg_idx == reg1:
                        continue
                    master_cpu.cores[core_id].coreStatus = 'IDLE'

            return
            


        elif opcode == Op.JOIN:
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context kan geen JOIN uitvoeren!")
                
            if not master_cpu.contexts:
                master_cpu.status = 0
                target.PC = arg2
                target.fsm_state = 'FETCH'
                return
            
            # Inspecteer de oudste actieve thread
            oudste_thread = master_cpu.contexts[0]
            
            if oudste_thread.fsm_state not in ['DONE', 'HALT', 'CLOSE']:
                master_cpu.status = 0       
                target.PC = arg2            
                target.fsm_state = 'FETCH'  
                return                      
                
            # Oogst de uCore-pointer uit de thread op de exacte register-index (reg1)
            thread_result_core = oudste_thread.registers[reg1]

            # HARDWARE CRITICAL: Het resultaat-register MAG NOOIT leeg (None) zijn bij een JOIN!
            if thread_result_core is None:
                raise RuntimeError(
                    f"Hardware Fault: Fatale dataflow-breuk! Thread resulterend register {reg1} "
                    f"bevat geen geldige uCore-pointer tijdens JOIN."
                )

            # if thread_result_core is not None:
                # VEILIGE HARDWARE CHECK: Is de resultaat-core al ECHT klaar?
            if master_cpu.cores[thread_result_core].coreStatus == 'WORKING':
                # De thread is DONE, maar de ALU-microcode tikt nog.
                # In plaats van de FSM te bevriezen in 'EXECUTE', springen we terug
                # naar het polling-adres zodat de simulator/uCores blijven tikken!
                master_cpu.status = 0
                target.PC = arg2            # Spring terug naar WAIT_FOR_THREAD
                target.fsm_state = 'FETCH'  # Geef de rest van de matrix ademruimte
                return
            
                # elif master_cpu.cores[thread_result_core].coreStatus == 'VALID':
                    # Draag de uCore-pointer direct over naar de CPU registers van de master
            master_cpu.registers[reg1] = thread_result_core
            master_cpu.last_active_core = thread_result_core
                
            # SCHOONMAAKWERK: Zet alle overige uCores van deze thread-context op IDLE
            for reg_idx, core_id in oudste_thread.registers.items():
                if core_id is not None:
                    if core_id == thread_result_core:
                        continue
                    master_cpu.cores[core_id].coreStatus = 'IDLE'
            
            # Ruim de context op uit de actieve lijst
            master_cpu.contexts.pop(0)
            master_cpu.status = 1           
            target.fsm_state = 'FETCH'

        # ==========================================
        #   NEW: IO-CONTROLLER BUS INSTRUCTIONS
        # ==========================================
        elif opcode == Op.OUT:
            # OUT Rx reg# -> reg1 is het CPU-register Rx, arg2 is het IO-registernummer
            core_id = target.registers[reg1]
            
            if core_id is None:
                raise RuntimeError(f"Hardware Fault: OUT gebruikt leeg register R{reg1}!")
                
            # Wacht tot de uCore van de dataflow-keten VALID is
            if master_cpu.cores[core_id].coreStatus != 'VALID':
                target.fsm_state = 'EXECUTE'  # Stall de FSM tot de waarde er is
                return
                
            value_to_send = master_cpu.cores[core_id].value
            
            # Praat met de IO-bus via de master_cpu koppeling
            if master_cpu.io_bus is not None:
                success = master_cpu.io_bus.cpu_out(reg_num=arg2, value=value_to_send)
                if not success:
                    # De IO-Controller gaf False (write_flag == 1). We moeten STALLEN!
                    target.fsm_state = 'EXECUTE'
                    return
            else:
                raise RuntimeError("Hardware Fault: OUT uitgevoerd maar geen IO-bus gekoppeld!")

            target.fsm_state = 'FETCH'

        elif opcode == Op.IN:
            # IN Rx reg# -> reg1 is het doelregister Rx, arg2 is het IO-registernummer
            if not master_cpu.free_cores: 
                target.fsm_state = 'EXECUTE'  # Stall als er geen uCores vrij zijn voor het resultaat
                return 
                
            if master_cpu.io_bus is not None:
                # Haal de waarde uit de controller
                io_value = master_cpu.io_bus.cpu_in(reg_num=arg2)
                
                # Allokeer een uCore om deze waarde vast te houden
                core_id = master_cpu.free_cores.popleft()
                master_cpu.cores[core_id].transfer = io_value
                master_cpu.cores[core_id].dispatch('ldv')
                
                # Koppel de core aan het register van het actieve target (master of context)
                target.registers[reg1] = core_id
                target.last_active_core = core_id
            else:
                raise RuntimeError("Hardware Fault: IN uitgevoerd maar geen IO-bus gekoppeld!")

            target.fsm_state = 'FETCH'

        elif opcode == Op.IOSYNC:
            # Non-blocking tick voor de controller
            if master_cpu.io_bus is not None:
                master_cpu.io_bus.cpu_iosync()
            else:
                raise RuntimeError("Hardware Fault: IOSYNC uitgevoerd maar geen IO-bus gekoppeld!")
                
            target.fsm_state = 'FETCH'


        # Zorg dat de standaardafhandeling de eigen FSM reset
        target.fsm_state = 'FETCH'







""" some example assemblycode 
ldi A 20        ; Laad A met 20
ldm B 20        ; Laad B met de waarde van $mem (adres 20)
add A B         ; tel A en B bij elkaar op
halt
"""