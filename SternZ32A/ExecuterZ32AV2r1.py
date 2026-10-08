
# Importeer de STERN-boekhouding uit het andere bestand
from opcodes import Op, FORMAT_ZERO, FORMAT_ONE_ADDR, FORMAT_ONE_REG, FORMAT_TWO_REG_REG, FORMAT_TWO_REG_VAL

class HardwareContext:
    def __init__(self, master_cpu, source_reg, direct_value=None, parent_cpu_id=None):
        self.parent_id = parent_cpu_id
        self.memory    = master_cpu.memory
        self.cores     = master_cpu.cores
        self.registers = {i: None for i in range(10)}

        # Lokale statusvlag per hardware-context
        self.status = 1

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

        # elif opcode == Op.SUCCES:
        #     if target != master_cpu:
        #         raise RuntimeError("Hardware Fault: Een sub-context mag geen SUCCES/FAIL uitvoeren!")
            
        #     if master_cpu.status == 1:
        #         master_cpu.PC = arg2
        #     master_cpu.fsm_state = 'FETCH'

        # elif opcode == Op.FAIL:
        #     if target != master_cpu:
        #         raise RuntimeError("Hardware Fault: Een sub-context mag geen SUCCES/FAIL uitvoeren!")
            
        #     if master_cpu.status == 0:
        #         master_cpu.PC = arg2
        #         master_cpu.status = 1
        #     master_cpu.fsm_state = 'FETCH'
        elif opcode == Op.SUCCES:
            # succes JumpTarget (spring als target.status == 1)
            if target.status:
                target.PC = arg2
            target.fsm_state = 'FETCH'

        elif opcode == Op.FAIL:
            # fail JumpTarget (spring als target.status == 0)
            if not target.status:
                target.PC = arg2
            target.fsm_state = 'FETCH'

        elif opcode == Op.SYNC:
            # sync FailPC
            # Check of er lokaal nog asynchrone sub-contexts draaien
            if len(master_cpu.contexts) > 0:
                # Er is nog activiteit! Spring naar het fail/wait label (arg2)
                target.PC = arg2
                target.status = 0
            else:
                # De lokale context-lijst is volledig leeg en stilgevallen. Succes!
                target.status = 1
                target.fsm_state = 'FETCH'  # Stroom geruisloos door naar de volgende regel


        elif opcode == Op.CONTEXT:
            # context RegA, JumpPC
            # Alleen de hoofd-CPU (master van dit executie-domein) mag sub-threads spawnen
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context probeerde zelf een CONTEXT te spawnen!")

            # 1. VALIDEER SOURCE uCORE (STALL als register A nog niet VALID is!)
            src_core_id = target.registers[reg1]
            if src_core_id is None:
                return
            
            core_src = master_cpu.cores[src_core_id]
            if core_src.coreStatus != 'VALID':
                return  # STALL: Wacht totdat de uCore 'VALID' is

            # 2. HARDWARE HIGH-WATERMARK CHECK (minstens 15 vrije uCores nodig)
            if len(master_cpu.free_cores) < 15:
                target.status = 0          # Signaleer FAIL lokaal op target context
                target.fsm_state = 'FETCH' # Niet stallen, maar fsm_state resetten
                return

            # 3. CONTEXT AANMAKEN
            # Omdat target == master_cpu is, halen we het parent_id veilig op
            parent_cpu_id = getattr(target, 'parent_cpu_id', getattr(target, 'ID', 0))
            nieuwe_ctx = HardwareContext(master_cpu, reg1, parent_cpu_id=parent_cpu_id)

            nieuwe_ctx.PC = arg2
            nieuwe_ctx.fsm_state = 'FETCH'
            
            master_cpu.contexts.append(nieuwe_ctx)
            target.fsm_state = 'FETCH'
            target.status = 1  # Signaleer SUCCES lokaal op target context

            # print("Local context started")

            # # === NIEUWE DEBUG PRINT REGEL ===
            # ctx_id = len(master_cpu.contexts) - 1
            # cores_over = len(master_cpu.free_cores)
            # # \033[38;2;0;255;50m dwingt exact die giftige, felle 'blood green' af
            # print(f"\033[38;2;0;255;50m[SPAWN] 🚀 Context #{ctx_id:02d} aangemaakt | Matrix pool: {cores_over} cores vrij\033[0m")
            # # =================================

        
        elif opcode == Op.RCONTEXT:
            # RCONTEXT arg_reg, task_pc (Remote Context Request)
            
            # 1. VALIDEER SOURCE uCORE (STALL als het argumentregister nog niet VALID is!)
            src_core_id = target.registers[reg1]
            if src_core_id is None: 
                return
                
            core_src = master_cpu.cores[src_core_id]
            if core_src.coreStatus != 'VALID':
                return  # STALL: Wacht 1 tick totdat de uCore klaar is!

            # 2. De uCore is VALID: lees de echte berekende waarde uit
            arg_reg = reg1
            arg_val = core_src.value
            task_pc = arg2

            # 3. CIU stelt het instructie-pakket samen en scant de aangesloten poorten
            ack = master_cpu.ciu.request_remote_context(
                task_pc, arg_reg, arg_val
            )

            # 4. STATUS OP DE LOKALE TARGET CONTEXT BIJWERKEN
            if ack:
                target.status = 1  # SUCCESS: Taak geaccepteerd door een buur!
            else:
                target.status = 0  # FAIL (NACK): Alle buren vol of niet aangesloten!

            # NIET STALLEN BIJ NACK! Ga direct door naar de opvang-instructie (bijv. FAIL / JMPF)
            target.fsm_state = "FETCH"

        elif opcode == Op.ALLSYNC:
            # Check 1: Draaien er lokaal nog actieve contexts op deze CPU?
            lokale_activiteit = len(master_cpu.contexts) > 0

            # Check 2: Vraag via de CIU of er op buur-CPU's nog activiteit is
            remote_activiteit = not master_cpu.ciu.are_all_neighbors_idle()

            if lokale_activiteit or remote_activiteit:
                # Er is nog activiteit in het cluster! Spring terug naar het sync-label (arg2)
                target.PC = arg2
                target.status = 0
            else:
                # Het gehele cluster (lokaal + remote) is 100% klaar!
                target.status = 1
                target.fsm_state = 'FETCH'  # Stroom geruisloos door naar de volgende instructie

        elif opcode == Op.RBOOT:
            # RBOOT link_reg, start_pc
            
            # 1. VALIDEER SOURCE uCORE (STALL als link_reg uCore nog niet VALID is)
            core_id = target.registers[reg1]
            if core_id is None:
                return
                
            core_link = master_cpu.cores[core_id]
            if core_link.coreStatus != 'VALID':
                return  # STALL: Wacht 1 tick totdat de uCore klaar is!

            # 2. De uCore is VALID: lees de echte link_id uit
            link_id = core_link.value
            start_pc = arg2

            # 3. Verstuur het boot-pakket via de CIU
            ack = master_cpu.ciu.send_boot_remote(link_id, start_pc)
            
            # 4. STATUS OP DE LOKALE TARGET CONTEXT BIJWERKEN
            if ack:
                target.status = 1  # SUCCESS: Remote CPU succesvol gewekt
            else:
                target.status = 0  # FAIL: Poort niet aangesloten of buur afwezig
                
            target.fsm_state = "FETCH"  # Stroom door naar de volgende regel

        elif opcode == Op.CLOSE:
            # close (Thread Completion Barrier)
            if target == master_cpu:
                raise RuntimeError("Hardware Fault: De master-CPU mag CLOSE niet aanroepen!")
            
            # 1. CONTROLEER OF ALLE GEBRUIKTE uCORES IN DEZE CONTEXT KLAAR ZIJN ('VALID')
            for reg_val in target.registers.values():
                if reg_val is not None:
                    assigned_core = master_cpu.cores[reg_val]
                    
                    # Als een uCore nog bezig is, dwingen we deze context om te stallen
                    if assigned_core.coreStatus == 'WORKING':
                        target.fsm_state = 'EXECUTE'
                        return 

            # 2. ALLE UCORES ZIJN VALID: Markeer deze sub-context als afgerond
            target.fsm_state = 'DONE'
            return

        elif opcode == Op.AUTOCLOSE:
            # autoclose (Fire-and-Forget Thread Termination)
            if target == master_cpu:
                raise RuntimeError("Hardware Fault: De master-CPU mag AUTOCLOSE niet aanroepen!")

            # 1. INTERLOCK CHECK: Wacht tot alle rekenketens in deze context 'VALID' zijn
            for core_id in target.registers.values():
                if core_id is not None:
                    if master_cpu.cores[core_id].coreStatus == 'WORKING':
                        target.fsm_state = 'EXECUTE'
                        return

            # 2. HARDWARE OPTIMALISATIE: Zet uCores direct op 'IDLE' voor 1-tick pool versnelling
            for core_id in target.registers.values():
                if core_id is not None:
                    master_cpu.cores[core_id].coreStatus = 'IDLE'

            # 3. Formele deactivatie van de thread
            target.fsm_state = 'HALT'

            # 4. Verwijder uit actieve contexts zodat de GC / pool dit direct opruimt
            if target in master_cpu.contexts:
                master_cpu.contexts.remove(target)

            return

        elif opcode == Op.JOIN:
            # join RegTarget, FailPC
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context kan geen JOIN uitvoeren!")

            # 1. CHECK OF ER NOG THREADS DRAAIEN
            if not master_cpu.contexts:
                target.status = 0
                target.PC = arg2            # Spring naar het fail/wait label
                target.fsm_state = 'FETCH'
                return

            # Inspecteer de oudste actieve thread
            oudste_thread = master_cpu.contexts[0]

            # 2. IS DE THREAD KLAAR MET ZIJN EXECUTIE-LUS?
            if oudste_thread.fsm_state not in ['DONE', 'HALT', 'CLOSE']:
                target.status = 0
                target.PC = arg2            # Thread draait nog: spring naar wait loop
                target.fsm_state = 'FETCH'
                return

            # 3. OOGST DE uCORE-POINTER UIT HET SPECIFIEKE RESULTAAT-REGISTER (reg1)
            thread_result_core = oudste_thread.registers.get(reg1)

            if thread_result_core is None:
                raise RuntimeError(
                    f"Hardware Fault: Fatale dataflow-breuk! Thread resulterend register {reg1} "
                    f"bevat geen geldige uCore-pointer tijdens JOIN."
                )

            # 4. HARDWARE CHECK: Is de uCore ook daadwerkelijk klaar?
            if master_cpu.cores[thread_result_core].coreStatus == 'WORKING':
                target.status = 0
                target.PC = arg2            # Spring terug naar wait loop
                target.fsm_state = 'FETCH'
                return

            # 5. OVERDRACHT: Wijs het berekende resultaat toe aan het master register
            master_cpu.registers[reg1] = thread_result_core

            # 6. OPBOOMEN / GARBAGE COLLECTION:
            # Geef alle interim uCores van deze thread (behalve het eindresultaat) direct vrij op 'IDLE'
            for reg_idx, core_id in oudste_thread.registers.items():
                if core_id is not None and core_id != thread_result_core:
                    master_cpu.cores[core_id].coreStatus = 'IDLE'

            # 7. CONTEXT VERWIJDEREN EN LOKALE STATUS SUCCES SIGNALEEREN
            master_cpu.contexts.pop(0)
            target.status = 1
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
            if rx_core_id is None or ry_core_id is None: 
                return
            
            core_rx = master_cpu.cores[rx_core_id]
            core_ry = master_cpu.cores[ry_core_id]
            
            if core_rx.coreStatus != 'VALID' or core_ry.coreStatus != 'VALID':
                return  # STALL: Wacht tot de uCores klaar zijn met rekenen!

            # 2. CONTROLEER VRIJE uCORE VOOR RESULTAAT (tx_slotID)
            if not master_cpu.free_cores: 
                return  # STALL: Geen vrije uCore beschikbaar voor de output

            # 3. WAARDEN UITLEZEN UIT DE VALID uCORES
            tag_val  = core_rx.value
            size_val = core_ry.value

            # 4. PARENT CPU ID BEPALEN
            parent_id = getattr(target, 'parent_cpu_id', getattr(target, 'parent_id', getattr(master_cpu, 'parent_id', 0)))

            # 5. MSG_START AANROEPEN (ontvangt nu Tuple: success, tx_id)
            success, tx_id = master_cpu.ciu.msg_start(tag_val, size_val, parent_id)

            # 6. STATUS VLAG BIJWERKEN (1 = SUCCES, 0 = FAIL)
            target.status = 1 if success else 0

            # 7. ALLEEN BIJ SUCCES RESULTAAT TOEWIJZEN AAN NIEUWE uCORE
            if success:
                core_id = master_cpu.free_cores.popleft()
                master_cpu.cores[core_id].transfer = tx_id
                master_cpu.cores[core_id].dispatch('ldv')
                target.registers[arg2] = core_id

        elif opcode == Op.MSG_WRITE:
            # msg_write Ry, Rx (reg1 = Ry [tx_slotID], arg2 = Rx [DATA])
            ry_core_id = target.registers[reg1]
            rx_core_id = target.registers[arg2]

            # 1. HARDWARE STALL: Wacht tot de uCores 'VALID' zijn
            if ry_core_id is None or rx_core_id is None:
                return

            core_ry = master_cpu.cores[ry_core_id]
            core_rx = master_cpu.cores[rx_core_id]

            if core_ry.coreStatus != 'VALID' or core_rx.coreStatus != 'VALID':
                return  # STALL: Wacht tot bijv. een eerdere berekening klaar is

            # 2. PAK WAARDEN UIT DE uCORES
            tx_id    = core_ry.value
            data_val = core_rx.value

            # 3. ROEP CIU AAN EN BIJWERK TARGET.STATUS
            success = master_cpu.ciu.msg_write(tx_id, data_val)
            target.status = 1 if success else 0

        elif opcode == Op.MSG_DONE:
            # msg_done Ry (reg1 = Ry [tx_slotID])
            ry_core_id = target.registers[reg1]

            # 1. HARDWARE STALL: Wacht tot de uCore VALID is
            if ry_core_id is None:
                return
            
            core_ry = master_cpu.cores[ry_core_id]
            if core_ry.coreStatus != 'VALID':
                return  # STALL: Wacht tot de uCore klaar is

            # 2. PAK HET TX_ID UIT DE uCORE
            tx_id = core_ry.value

            # 3. ROEP CIU AAN EN BIJWERK TARGET.STATUS
            success = master_cpu.ciu.msg_done(tx_id)
            target.status = 1 if success else 0

        elif opcode == Op.MSG_OPEN:
            # msg_open Rx (reg1 = Rx [ontvangt rx_slotID])
            
            # 1. CONTROLEER VRIJE uCORE VOOR HET RESULTAAT (rx_slotID)
            if not master_cpu.free_cores:
                return  # STALL: Geen vrije uCore beschikbaar

            # 2. ROEP CIU AAN (ontvangt tuple: success, rx_id)
            success, rx_id = master_cpu.ciu.msg_open()

            # 3. ZET STATUS OP HET TARGET CONTEXT
            target.status = 1 if success else 0

            # 4. WIJS uCORE TOE BIJ SUCCES
            if success:
                core_id = master_cpu.free_cores.popleft()
                master_cpu.cores[core_id].transfer = rx_id
                master_cpu.cores[core_id].dispatch('ldv')
                target.registers[reg1] = core_id

        
        elif opcode == Op.MSG_PROBE:
            # msg_probe Rx (reg1 = Rx [expected_tag])
            rx_core_id = target.registers[reg1]

            # 1. HARDWARE STALL: Wacht tot de uCore 'VALID' is
            if rx_core_id is None:
                return

            core_rx = master_cpu.cores[rx_core_id]
            if core_rx.coreStatus != 'VALID':
                return  # STALL: Wacht tot de uCore klaar is met rekenen

            # 2. PAK DE TAG-WAARDE UIT DE uCORE
            expected_tag = core_rx.value

            # 3. ROEP CIU AAN EN BIJWERK TARGET.STATUS
            match = master_cpu.ciu.msg_probe(expected_tag)
            target.status = 1 if match else 0

        elif opcode == Op.MSG_READ:
            # msg_read Ry, Rx (reg1 = Ry [rx_slotID], arg2 = Rx [ontvangt DATA])
            ry_core_id = target.registers[reg1]

            # 1. HARDWARE STALL: Wacht tot de uCore met het slot_id VALID is
            if ry_core_id is None:
                return

            core_ry = master_cpu.cores[ry_core_id]
            if core_ry.coreStatus != 'VALID':
                return  # STALL: Wacht tot de uCore klaar is

            # 2. CONTROLEER VRIJE uCORE VOOR HET RESULTAAT (de gelezen data)
            if not master_cpu.free_cores:
                return  # STALL: Geen vrije uCore beschikbaar voor output

            # 3. PAK HET RX_SLOT_ID UIT DE uCORE
            rx_slot_id = core_ry.value

            # 4. ROEP CIU AAN (ontvangt tuple: success, data_val)
            success, data_val = master_cpu.ciu.msg_read(rx_slot_id)

            # 5. STATUS VLAG OP DE HARDWARECONTEXT BIJWERKEN
            target.status = 1 if success else 0

            # 6. ALLEEN BIJ SUCCES RESULTAAT TOEWIJZEN AAN NIEUWE uCORE
            if success:
                core_id = master_cpu.free_cores.popleft()
                master_cpu.cores[core_id].transfer = data_val
                master_cpu.cores[core_id].dispatch('ldv')
                target.registers[arg2] = core_id

        elif opcode == Op.MSG_CLOSE:
            # msg_close Ry (reg1 = Ry [rx_slotID])
            ry_core_id = target.registers[reg1]

            # 1. HARDWARE STALL: Wacht tot de uCore met het slot_id VALID is
            if ry_core_id is None:
                return

            core_ry = master_cpu.cores[ry_core_id]
            if core_ry.coreStatus != 'VALID':
                return  # STALL: Wacht tot de uCore klaar is met rekenen

            # 2. PAK HET RX_SLOT_ID UIT DE uCORE
            rx_slot_id = core_ry.value

            # 3. ROEP CIU AAN EN BIJWERK TARGET.STATUS
            success = master_cpu.ciu.msg_close(rx_slot_id)
            target.status = 1 if success else 0

        
        
        
        # Zorg dat de standaardafhandeling de eigen FSM reset
        target.fsm_state = 'FETCH'
