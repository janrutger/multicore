if opcode == Op.CONTEXT:
            # Alleen de hoofd-CPU (master van dit executie-domein) mag sub-threads spawnen
            if target != master_cpu:
                raise RuntimeError("Hardware Fault: Een sub-context probeerde zelf een CONTEXT te spawnen!")
                
            # 1. VALIDEER SOURCE uCORE (STALL als register A nog niet VALID is!)
            src_core_id = target.registers[reg1]
            if src_core_id is None: return
            core_src = master_cpu.cores[src_core_id]
            if core_src.coreStatus != 'VALID':
                return  # STALL: Wacht 1 tick totdat L -> A klaar is!

            # 2. HARDWARE HIGH-WATERMARK CHECK
            if len(master_cpu.free_cores) < 15:
                target.status = 0              # Signaleer FAIL naar target status
                target.fsm_state = 'FETCH'     # Niet stallen op high-watermark
                return
            
            # 3. Allocatie is gegarandeerd succesvol! Maak nu pas de hardware context aan
            parent_cpu_id = target.ID
            nieuwe_ctx = HardwareContext(master_cpu, reg1, parent_cpu_id=parent_cpu_id)
                
            nieuwe_ctx.PC = arg2
            nieuwe_ctx.fsm_state = 'FETCH'
            master_cpu.contexts.append(nieuwe_ctx)
            target.fsm_state = 'FETCH'
            target.status = 1

elif opcode == Op.RCONTEXT:
    # RCONTEXT arg_reg, task_pc
    # 1. VALIDEER SOURCE uCORE (STALL als het argumentregister nog niet VALID is!)
    src_core_id = target.registers[reg1]
    if src_core_id is None: return
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

    if ack:
        target.status = 1  # SUCCESS: Taak geaccepteerd door een buur!
    else:
        target.status = 0  # FAIL (NACK): Alle buren vol of niet aangesloten!

    # NIET STALLEN BIJ NACK! Ga direct door naar de opvang-instructie (bijv. JMPF)
    target.fsm_state = "FETCH"

elif opcode == Op.ALLSYNC:
    # Check 1: Draaien er lokaal nog actieve contexts of cores?
    lokale_activiteit = len(master_cpu.contexts) > 0

    # Check 2: Vraag via de CIU of er op buur-CPU's nog activiteit is
    remote_activiteit = not master_cpu.ciu.are_all_neighbors_idle()

    if lokale_activiteit or remote_activiteit:
        # Er is nog activiteit in het cluster! Spring terug naar het label (arg2)
        target.PC = arg2
        target.status = 0
    else:
        # Het gehele cluster (lokaal + remote) is 100% klaar!
        target.status = 1
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
        target.status = 1  # SUCCESS: Remote CPU succesvol gewekt
    else:
        target.status = 0  # FAIL: Poort niet aangesloten of buur afwezig
        
    target.fsm_state = "FETCH"  # Stroom door naar de volgende regel

elif opcode == Op.CLOSE:
    if target == master_cpu:
        raise RuntimeError("Hardware Fault: De master-CPU mag CLOSE niet aanroepen!")
    
    # We lopen door de registers van de thread
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
        target.status = 0
        target.PC = arg2
        target.fsm_state = 'FETCH'
        return
    
    # Inspecteer de oudste actieve thread
    oudste_thread = master_cpu.contexts[0]
    
    if oudste_thread.fsm_state not in ['DONE', 'HALT', 'CLOSE']:
        target.status = 0       
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

    # VEILIGE HARDWARE CHECK: Is de resultaat-core al ECHT klaar?
    if master_cpu.cores[thread_result_core].coreStatus == 'WORKING':
        target.status = 0
        target.PC = arg2            # Spring terug naar WAIT_FOR_THREAD
        target.fsm_state = 'FETCH'  # Geef de rest van de matrix ademruimte
        return
    
    # Draag de uCore-pointer direct over naar de CPU registers van de master
    master_cpu.registers[reg1] = thread_result_core
        
    # SCHOONMAAKWERK: Zet alle overige uCores van deze thread-context op IDLE
    for reg_idx, core_id in oudste_thread.registers.items():
        if core_id is not None:
            if core_id == thread_result_core:
                continue
            master_cpu.cores[core_id].coreStatus = 'IDLE'
    
    # Ruim de context op uit de actieve lijst
    master_cpu.contexts.pop(0)
    target.status = 1           
    target.fsm_state = 'FETCH'