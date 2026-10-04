
# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class HardwareContext:
    def __init__(self, master_cpu, source_reg, direct_value=None, parent_cpu_id=None):
        self.parent_id = parent_cpu_id
        self.memory    = master_cpu.memory
        self.cores     = master_cpu.cores
        self.registers = {i: None for i in range(10)}

        # print(self.parent_id)     # DEBUG print

        # Als er een direct_value is meegegeven (via CIU RCONTEXT), gebruiken we die!
        if direct_value is not None:
            source_value = direct_value
        else:
            # Anders lezen we de waarde traditioneel uit het hoofdregister van de CPU
            source_core_id = master_cpu.registers[source_reg]
            if source_core_id is None:
                raise RuntimeError(
                    f"Hardware Fault: Register {source_reg} bevat geen geldige"
                    " ucore-wijzer!"
                )
            source_value = master_cpu.cores[source_core_id].value

        if not master_cpu.free_cores:
            master_cpu.status = 0
        else:
            allocated_core_id = master_cpu.free_cores.popleft()
            master_cpu.status = 1

            target_core = master_cpu.cores[allocated_core_id]
            target_core.value = source_value
            target_core.coreStatus = "VALID"
            target_core.upc = 0
            target_core.status = True
            target_core.work = 0
            target_core.transfer = 0
            target_core.sign_v = 0
            target_core.sign_w = 0

            self.registers[source_reg] = allocated_core_id

            self.fsm_state = "FETCH"
            self.MIR = None
            self.PC = 0
            self.decoded_opcode = 0
            self.decoded_reg1 = 0
            self.decoded_arg2 = 0
            # self.last_active_core = allocated_core_id
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
            # target.last_active_core = core_id

        elif opcode == Op.LD:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
        
            master_cpu.cores[core_id].dispatch('ld', arg1=src1_core, arg2=src2_core) 
            target.registers[reg1] = core_id
            # target.last_active_core = core_id
        
        elif opcode == Op.CPUID:
            if not master_cpu.free_cores: return # Stall als er geen vrije uCores zijn
            core_id = master_cpu.free_cores.popleft()
            
            # Haal het ID op van de huidige CPU
            cpu_id_value = master_cpu.ID
            
            # Laad de waarde via het uCore transfer mechanisme
            master_cpu.cores[core_id].transfer = cpu_id_value
            master_cpu.cores[core_id].dispatch('ldv') 
            
            # Sla het uCore ID op in het bestemmingsregister
            target.registers[reg1] = core_id

        elif opcode == Op.PID:
            if not master_cpu.free_cores: return # Stall als er geen vrije uCores zijn
            core_id = master_cpu.free_cores.popleft()
            
            # Haal het parent CPU ID op uit de actieve hardware context (target)
            # Valt terug op het eigen master_cpu.ID als parent_id om een of andere reden None is
            parent_id_value = target.parent_id if target.parent_id is not None else master_cpu.ID
            
            # Laad de waarde via het uCore transfer mechanisme
            master_cpu.cores[core_id].transfer = parent_id_value
            master_cpu.cores[core_id].dispatch('ldv') 
            
            # Sla het uCore ID op in het bestemmingsregister (Rx / reg1)
            target.registers[reg1] = core_id

        elif opcode == Op.LDM:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            mem_value = master_cpu.memory.memRead(arg2, master_cpu.ID)
            
            master_cpu.cores[core_id].transfer = mem_value
            master_cpu.cores[core_id].dispatch('ldv') 
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.LDX:
            # LDX Rx mem_base -> Gebruikt target index-register R0
            index_core = target.registers[0]  
            
            if index_core is not None and master_cpu.cores[index_core].coreStatus == 'VALID':
                if not master_cpu.free_cores: return          # Fast Stall
                core_id = master_cpu.free_cores.popleft()     

                effective_addr = arg2 + master_cpu.cores[index_core].value
                ram_value = master_cpu.memory.memRead(effective_addr, master_cpu.ID)
                
                master_cpu.cores[core_id].transfer = ram_value
                master_cpu.cores[core_id].dispatch('ldv') 
                target.registers[reg1] = core_id
                # target.last_active_core = core_id
            else:
                return  # Stall

        elif opcode == Op.ADD:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('add', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id    

        elif opcode == Op.SUB:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('sub', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id         
            
        elif opcode == Op.MUL:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('mul', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.DIV:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('div', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id


        elif opcode == Op.ADDI:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2
            
            master_cpu.cores[core_id].dispatch('addi', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.SUBI:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2
            
            master_cpu.cores[core_id].dispatch('subi', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.MULI:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2
            
            master_cpu.cores[core_id].dispatch('muli', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.DIVI:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2
            
            master_cpu.cores[core_id].dispatch('divi', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.INC:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]

            master_cpu.cores[core_id].dispatch('inc', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.DEC:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]

            master_cpu.cores[core_id].dispatch('dec', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.MOD:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('mod', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.XOR:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2] 
            
            master_cpu.cores[core_id].dispatch('xor_vw', arg1=src1_core, arg2=src2_core)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.SHIFTL:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('shftl', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.SHIFTR:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('shftr', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.SM32_RND:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('sm32_rnd', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.ROTL32:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2

            master_cpu.cores[core_id].dispatch('rol32', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id

        elif opcode == Op.TST:   # TST Rx == value 
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            master_cpu.cores[core_id].transfer = arg2
            
            master_cpu.cores[core_id].dispatch('tst', arg1=src1_core, arg2=None)

            target.registers[reg1] = core_id
            # target.last_active_core = core_id
            target.last_test_core = core_id  # Lokaal vastleggen voor target sprongen

        elif opcode == Op.TSTE:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2]
            
            master_cpu.cores[core_id].dispatch('cmpe', arg1=src1_core, arg2=src2_core)

            target.registers[reg1] = core_id
            # target.last_active_core = core_id
            target.last_test_core = core_id  # Lokaal vastleggen voor target sprongen

        elif opcode == Op.TSTG:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()
            
            src1_core = target.registers[reg1]
            src2_core = target.registers[arg2]
            
            master_cpu.cores[core_id].dispatch('cmpgt', arg1=src1_core, arg2=src2_core)

            target.registers[reg1] = core_id
            # target.last_active_core = core_id
            target.last_test_core = core_id  # Lokaal vastleggen voor target sprongen

        elif opcode == Op.TSTZ:
            if not master_cpu.free_cores: return # Stall
            core_id = master_cpu.free_cores.popleft()

            src1_core = target.registers[reg1]

            master_cpu.cores[core_id].dispatch('tstz', arg1=src1_core, arg2=None)
            target.registers[reg1] = core_id
            # target.last_active_core = core_id
            target.last_test_core = core_id  # Lokaal vastleggen voor target sprongen


        # ==========================================
        #   SYSTEM / FLOW CONTROL
        # ==========================================
        elif opcode == Op.HALT:
            target.fsm_state = 'HALT'
            return

        elif opcode == Op.SUSPEND:
            target.fsm_state = 'WAIT_FOR_WORK'
            return
        

        elif opcode == Op.STO:
            core_id = target.registers[reg1]

            if core_id is None:
                raise RuntimeError(
                    f"Hardware Fault: STO op PC={target.PC-1} (MIR={target.MIR}). "
                    f"Register {reg1} heeft geen actieve Core-ID!"
                )

            if master_cpu.cores[core_id].coreStatus != 'VALID':
                return # Stall (wacht tot bron-core VALID is)

            value_to_store = master_cpu.cores[core_id].value

            # Schrijf naar MMU met ID en controleer op bus-stall
            status = master_cpu.memory.memWrite(value_to_store, adres=arg2, cpu_id=master_cpu.ID)
            if status == "STALL":
                return # Bus bezet door andere CPU: probeer volgende cyclus opnieuw

        elif opcode == Op.STX:
            index_core = target.registers[0]
            data_core = target.registers[reg1]

            if (index_core is not None and master_cpu.cores[index_core].coreStatus == 'VALID' and
                data_core is not None and master_cpu.cores[data_core].coreStatus == 'VALID'):

                effective_addr = arg2 + master_cpu.cores[index_core].value
                val_to_store = master_cpu.cores[data_core].value

                # Schrijf naar MMU met ID en controleer op bus-stall
                status = master_cpu.memory.memWrite(val_to_store, adres=effective_addr, cpu_id=master_cpu.ID)
                if status == "STALL":
                    return # Bus bezet door andere CPU: probeer volgende cyclus opnieuw
            else:
                return  # Stall (wacht tot index en data cores beide VALID zijn)

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
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context mag geen SUCCES/FAIL uitvoeren!")
            
            if master_cpu.status == 1:
                master_cpu.PC = arg2
            master_cpu.fsm_state = 'FETCH'

        elif opcode == Op.FAIL:
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context mag geen SUCCES/FAIL uitvoeren!")
            
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
            if len(master_cpu.free_cores) < 15:
                master_cpu.status = 0          # Signaleer FAIL naar de CPU status
                target.fsm_state = 'FETCH'     # NIET STALLEN! Ga direct naar de volgende instructie (FAIL)
                return                         # Breek de CONTEXT-allocatie veilig af
            
            # 2. Allocatie is gegarandeerd succesvol! Maak nu pas de hardware context aan
            parent_cpu_id = master_cpu.ID
            nieuwe_ctx = HardwareContext(master_cpu, reg1, parent_cpu_id=parent_cpu_id)
                
            # 3. Configureer de startparameters van de thread
            nieuwe_ctx.PC = arg2            # Dit wordt het startadres (bijv. 11)
            nieuwe_ctx.fsm_state = 'FETCH'  # Activeer de thread direct voor de scheduler
            
            # 4. Voeg hem toe aan de actieve contexts lijst
            master_cpu.contexts.append(nieuwe_ctx)
            target.fsm_state = 'FETCH'
            master_cpu.state = 1            # Signaleer succes naar de CPU (27sept26)

            # # === NIEUWE DEBUG PRINT REGEL ===
            # ctx_id = len(master_cpu.contexts) - 1
            # cores_over = len(master_cpu.free_cores)
            # # \033[38;2;0;255;50m dwingt exact die giftige, felle 'blood green' af
            # print(f"\033[38;2;0;255;50m[SPAWN] 🚀 Context #{ctx_id:02d} aangemaakt | Matrix pool: {cores_over} cores vrij\033[0m")
            # # =================================

        elif opcode == Op.RCONTEXT:
            # RCONTEXT arg_reg, task_pc
            # 1. Evalueer de data-waarde van het argument-register op DEZE CPU
            arg_reg = reg1
            arg_val = (
                master_cpu.cores[target.registers[reg1]].value
                if target.registers[reg1] is not None
                else 0
            )
            task_pc = arg2

            # 2. CIU stelt het instructie-pakket samen en scant de aangesloten poorten
            ack = master_cpu.ciu.request_remote_context(
                task_pc, arg_reg, arg_val
            )

            if ack:
                master_cpu.status = (
                    1  # SUCCESS: Taak geaccepteerd door een buur!
                )
            else:
                master_cpu.status = (
                    0  # FAIL (NACK): Alle buren vol of niet aangesloten!
                )

            # NIET STALLEN! Ga direct door naar de opvang-instructie (FAIL _count)
            target.fsm_state = "FETCH"

        elif opcode == Op.ALLSYNC:
            # Check 1: Draaien er lokaal nog actieve contexts of cores?
            lokale_activiteit = len(master_cpu.contexts) > 0

            # Check 2: Vraag via de CIU of er op buur-CPU's nog activiteit is
            remote_activiteit = not master_cpu.ciu.are_all_neighbors_idle()

            if lokale_activiteit or remote_activiteit:
                # Er is nog activiteit in het cluster! Spring terug naar het label (arg2)
                target.PC = arg2
                master_cpu.status = 0
            else:
                # Het gehele cluster (lokaal + remote) is 100% klaar!
                master_cpu.status = 1
                target.fsm_state = (
                    'FETCH'  # Stroom geruisloos door naar de volgende regel
                )

        elif opcode == Op.RBOOT:
            # RBOOT link_reg, start_pc
            # 1. Haal de uCore-index op en lees de daadwerkelijke link_id waarde uit
            core_id = target.registers[reg1]
            link_id = (
                master_cpu.cores[core_id].value
                if core_id is not None
                else 0
            )
            start_pc = arg2
    
            # 2. Verstuur het boot-pakket over de fysieke bus via de juiste link
            ack = master_cpu.ciu.send_boot_remote(link_id, start_pc)
            
            if ack:
                master_cpu.status = 1  # SUCCESS: Remote CPU succesvol gewekt
            else:
                master_cpu.status = 0  # FAIL: Poort niet aangesloten of buur afwezig
                
            target.fsm_state = "FETCH"  # Stroom door naar de volgende regel


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

        elif opcode == Op.AUTOCLOSE:
            if target == master_cpu:
                raise RuntimeError("Hardware Fault: De master-CPU mag AUTOCLOSE niet aanroepen!")
            
            # 1. Interlock check: Wacht tot de microcode op alle rekenketens 'VALID' is
            for core_id in target.registers.values():
                if core_id is not None:
                    if master_cpu.cores[core_id].coreStatus == 'WORKING':
                        target.fsm_state = 'EXECUTE'
                        return 

            # 2. HARDWARE OPTIMALISATIE: Zet cores direct op IDLE voor 1-tick pool versnelling!
            for core_id in target.registers.values():
                if core_id is not None:
                    master_cpu.cores[core_id].coreStatus = 'IDLE'

            # 3. Formele deactivatie van de thread
            target.fsm_state = 'HALT'

            # 4. Verwijder uit contexts -> GC STAP A pakt de IDLE cores in dezelfde tik direct op!
            if target in master_cpu.contexts:
                master_cpu.contexts.remove(target)
                
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
            # master_cpu.last_active_core = thread_result_core
                
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
                # target.last_active_core = core_id
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

        

        # =========================================================================
        #   CIU MAILBOX INSTRUCTIES (Met uCore Status Synchronisatie & Stalling)
        # =========================================================================

        elif opcode == Op.MSG_START:
            # msg_start Rx, Ry  (reg1 = Rx [TAG], arg2 = Ry [SIZE -> ontvangt tx_slotID])
            rx_core_id = target.registers[reg1]
            ry_core_id = target.registers[arg2]

            # 1. VALIDEER SOURCE uCORES (Stall als TAG of SIZE nog niet VALID zijn!)
            if rx_core_id is None or ry_core_id is None: return
            core_rx = master_cpu.cores[rx_core_id]
            core_ry = master_cpu.cores[ry_core_id]
            if core_rx.coreStatus != 'VALID' or core_ry.coreStatus != 'VALID':
                return  # STALL: Wacht tot uCores klaar zijn!

            # 2. CONTROLEER VRIJE uCORE VOOR RESULTAAT (tx_slotID)
            if not master_cpu.free_cores: return  # STALL

            tag_val  = core_rx.value
            size_val = core_ry.value

            parent_id = getattr(target, 'parent_id', getattr(master_cpu, 'parent_id', 0))

            tx_id = master_cpu.ciu.msg_start(tag_val, size_val, parent_id)

            # Sla gegenereerde tx_slotID op in een nieuwe uCore voor Ry (arg2)
            core_id = master_cpu.free_cores.popleft()
            master_cpu.cores[core_id].transfer = tx_id
            master_cpu.cores[core_id].dispatch('ldv')
            target.registers[arg2] = core_id

        elif opcode == Op.MSG_WRITE:
            # msg_write Ry, Rx  (reg1 = Ry [tx_slotID], arg2 = Rx [DATA])
            ry_core_id = target.registers[reg1]
            rx_core_id = target.registers[arg2]

            # VALIDEER SOURCE uCORES (Stall als tx_slotID of DATA (bijv. MUL) nog niet VALID is!)
            if ry_core_id is None or rx_core_id is None: return
            core_ry = master_cpu.cores[ry_core_id]
            core_rx = master_cpu.cores[rx_core_id]
            if core_ry.coreStatus != 'VALID' or core_rx.coreStatus != 'VALID':
                return  # STALL: Wacht tot bijv. MUL A A klaar is!

            tx_id    = core_ry.value
            data_val = core_rx.value

            master_cpu.ciu.msg_write(tx_id, data_val)

        elif opcode == Op.MSG_DONE:
            # msg_done Ry       (reg1 = Ry [tx_slotID])
            ry_core_id = target.registers[reg1]

            if ry_core_id is None: return
            core_ry = master_cpu.cores[ry_core_id]
            if core_ry.coreStatus != 'VALID':
                return  # STALL

            tx_id = core_ry.value
            master_cpu.ciu.msg_done(tx_id)

        elif opcode == Op.MSG_OPEN:
            # msg_open Rx       (reg1 = Rx [Ontvangt read_slotID])
            if not master_cpu.free_cores: return  # STALL

            rx_id = master_cpu.ciu.msg_open()

            core_id = master_cpu.free_cores.popleft()
            master_cpu.cores[core_id].transfer = rx_id
            master_cpu.cores[core_id].dispatch('ldv')
            target.registers[reg1] = core_id

        # elif opcode == Op.MSG_PROBE:
        #     # msg_probe Ry, Rx  (reg1 = Ry [read_slotID], arg2 = Rx [Ontvangt TAG])
        #     ry_core_id = target.registers[reg1]

        #     if ry_core_id is None: return
        #     core_ry = master_cpu.cores[ry_core_id]
        #     if core_ry.coreStatus != 'VALID':
        #         return  # STALL

        #     if not master_cpu.free_cores: return  # STALL voor destination uCore

        #     read_id = core_ry.value
        #     tag_val = master_cpu.ciu.msg_probe(read_id)
        # elif opcode == Op.MSG_PROBE:
        #     # msg_probe Rx      (reg1 = Rx [Ontvangt geïnspecteerde TAG van read_pointer])
        #     if not master_cpu.free_cores: return  # STALL voor destination uCore

        #     tag_val = master_cpu.ciu.msg_probe()

        #     # Ken een uCore toe om de uitgelezen TAG op te slaan in register Rx (reg1)
        #     core_id = master_cpu.free_cores.popleft()
        #     master_cpu.cores[core_id].transfer = tag_val
        #     master_cpu.cores[core_id].dispatch('ldv')
        #     target.registers[reg1] = core_id

        #     core_id = master_cpu.free_cores.popleft()
        #     master_cpu.cores[core_id].transfer = tag_val
        #     master_cpu.cores[core_id].dispatch('ldv')
        #     target.registers[arg2] = core_id
        elif opcode == Op.MSG_PROBE:
            # msg_probe Rx  (reg1 = Rx [Bevat de VERWACHTE TAG])
            rx_core_id = target.registers[reg1]

            # 1. Wacht tot de uCore met de verwachte TAG de status 'VALID' heeft (Stall)
            if rx_core_id is None: return
            core_rx = master_cpu.cores[rx_core_id]
            if core_rx.coreStatus != 'VALID':
                return  # STALL

            expected_tag = core_rx.value

            # 2. Voer Hardware Tag Match uit op de CIU (stelt zelf self.cpu.status in!)
            # NUL uCores nodig voor het opslaan van resultaten!
            master_cpu.ciu.msg_probe(expected_tag)

        elif opcode == Op.MSG_READ:
            # msg_read Ry, Rx   (reg1 = Ry [read_slotID], arg2 = Rx [Ontvangt DATA])
            ry_core_id = target.registers[reg1]

            if ry_core_id is None: return
            core_ry = master_cpu.cores[ry_core_id]
            if core_ry.coreStatus != 'VALID':
                return  # STALL

            if not master_cpu.free_cores: return  # STALL voor destination uCore

            read_id = core_ry.value
            data_val = master_cpu.ciu.msg_read(read_id)

            core_id = master_cpu.free_cores.popleft()
            master_cpu.cores[core_id].transfer = data_val
            master_cpu.cores[core_id].dispatch('ldv')
            target.registers[arg2] = core_id

        elif opcode == Op.MSG_CLOSE:
            # msg_close Ry      (reg1 = Ry [read_slotID])
            ry_core_id = target.registers[reg1]

            if ry_core_id is None: return
            core_ry = master_cpu.cores[ry_core_id]
            if core_ry.coreStatus != 'VALID':
                return  # STALL

            read_id = core_ry.value
            master_cpu.ciu.msg_close(read_id)

        
        
        
        # Zorg dat de standaardafhandeling de eigen FSM reset
        target.fsm_state = 'FETCH'
