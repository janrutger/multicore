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

        if direct_value is not None:
            source_value = direct_value
        else:
            source_core_id = master_cpu.registers[source_reg]
            if source_core_id is None:
                raise RuntimeError(
                    f"Hardware Fault: Register {source_reg} bevat geen geldige ucore-wijzer!"
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


# =========================================================================
# HELPER FUNCTIES VOOR UCORE REKENINSTRUCTIES
# =========================================================================

def _exec_binary_ucore(master_cpu, target, op_name, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    src2_core = target.registers[arg2]
    master_cpu.cores[core_id].dispatch(op_name, arg1=src1_core, arg2=src2_core)
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _exec_imm_ucore(master_cpu, target, op_name, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    master_cpu.cores[core_id].transfer = arg2
    master_cpu.cores[core_id].dispatch(op_name, arg1=src1_core, arg2=None)
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'


# =========================================================================
# HANDLERS PER INSTRUCTIE (DISPATCH TARGETS)
# =========================================================================

# --- COMPUTE & DATA TRANSFER HANDLERS ---
def _h_ldi(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    master_cpu.cores[core_id].transfer = arg2
    master_cpu.cores[core_id].dispatch('ldv')
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _h_ld(master_cpu, target, reg1, arg2):
    _exec_binary_ucore(master_cpu, target, 'ld', reg1, arg2)

def _h_cpu_id(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    master_cpu.cores[core_id].transfer = master_cpu.ID
    master_cpu.cores[core_id].dispatch('ldv')
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _h_pid(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    parent_id_value = target.parent_id if target.parent_id is not None else master_cpu.ID
    master_cpu.cores[core_id].transfer = parent_id_value
    master_cpu.cores[core_id].dispatch('ldv')
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _h_ldm(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    mem_value = master_cpu.memory.memRead(arg2, master_cpu.ID)
    master_cpu.cores[core_id].transfer = mem_value
    master_cpu.cores[core_id].dispatch('ldv')
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _h_ldx(master_cpu, target, reg1, arg2):
    index_core = target.registers[0]
    if index_core is not None and master_cpu.cores[index_core].coreStatus == 'VALID':
        if not master_cpu.free_cores:
            target.fsm_state = 'EXECUTE'
            return
            
        core_id = master_cpu.free_cores.popleft()
        effective_addr = arg2 + master_cpu.cores[index_core].value
        ram_value = master_cpu.memory.memRead(effective_addr, master_cpu.ID)
        
        master_cpu.cores[core_id].transfer = ram_value
        master_cpu.cores[core_id].dispatch('ldv')
        target.registers[reg1] = core_id
        target.fsm_state = 'FETCH'
    else:
        target.fsm_state = 'EXECUTE'

def _h_add(master_cpu, target, reg1, arg2):    _exec_binary_ucore(master_cpu, target, 'add', reg1, arg2)
def _h_sub(master_cpu, target, reg1, arg2):    _exec_binary_ucore(master_cpu, target, 'sub', reg1, arg2)
def _h_mul(master_cpu, target, reg1, arg2):    _exec_binary_ucore(master_cpu, target, 'mul', reg1, arg2)
def _h_div(master_cpu, target, reg1, arg2):    _exec_binary_ucore(master_cpu, target, 'div', reg1, arg2)
def _h_mod(master_cpu, target, reg1, arg2):    _exec_binary_ucore(master_cpu, target, 'mod', reg1, arg2)
def _h_xor(master_cpu, target, reg1, arg2):    _exec_binary_ucore(master_cpu, target, 'xor_vw', reg1, arg2)

def _h_addi(master_cpu, target, reg1, arg2):   _exec_imm_ucore(master_cpu, target, 'addi', reg1, arg2)
def _h_subi(master_cpu, target, reg1, arg2):   _exec_imm_ucore(master_cpu, target, 'subi', reg1, arg2)
def _h_muli(master_cpu, target, reg1, arg2):   _exec_imm_ucore(master_cpu, target, 'muli', reg1, arg2)
def _h_divi(master_cpu, target, reg1, arg2):   _exec_imm_ucore(master_cpu, target, 'divi', reg1, arg2)
def _h_shiftl(master_cpu, target, reg1, arg2): _exec_imm_ucore(master_cpu, target, 'shftl', reg1, arg2)
def _h_shiftr(master_cpu, target, reg1, arg2): _exec_imm_ucore(master_cpu, target, 'shftr', reg1, arg2)
def _h_sm32_rnd(master_cpu, target, reg1, arg2): _exec_imm_ucore(master_cpu, target, 'sm32_rnd', reg1, arg2)
def _h_rotl32(master_cpu, target, reg1, arg2): _exec_imm_ucore(master_cpu, target, 'rol32', reg1, arg2)

def _h_inc(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    master_cpu.cores[core_id].dispatch('inc', arg1=src1_core, arg2=None)
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _h_dec(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    master_cpu.cores[core_id].dispatch('dec', arg1=src1_core, arg2=None)
    target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

# --- COMPARISON & TEST HANDLERS ---
def _h_tst(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    master_cpu.cores[core_id].transfer = arg2
    master_cpu.cores[core_id].dispatch('tst', arg1=src1_core, arg2=None)
    target.registers[reg1] = core_id
    target.last_test_core = core_id
    target.fsm_state = 'FETCH'

def _h_tste(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    src2_core = target.registers[arg2]
    master_cpu.cores[core_id].dispatch('cmpe', arg1=src1_core, arg2=src2_core)
    target.registers[reg1] = core_id
    target.last_test_core = core_id
    target.fsm_state = 'FETCH'

def _h_tstg(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    src2_core = target.registers[arg2]
    master_cpu.cores[core_id].dispatch('cmpgt', arg1=src1_core, arg2=src2_core)
    target.registers[reg1] = core_id
    target.last_test_core = core_id
    target.fsm_state = 'FETCH'

def _h_tstz(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
    core_id = master_cpu.free_cores.popleft()
    src1_core = target.registers[reg1]
    master_cpu.cores[core_id].dispatch('tstz', arg1=src1_core, arg2=None)
    target.registers[reg1] = core_id
    target.last_test_core = core_id
    target.fsm_state = 'FETCH'

# --- MEMORY STORE HANDLERS ---
def _h_sto(master_cpu, target, reg1, arg2):
    core_id = target.registers[reg1]
    if core_id is None:
        raise RuntimeError(f"Hardware Fault: STO op PC={target.PC-1}. Reg {reg1} is leeg!")
    
    if master_cpu.cores[core_id].coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return
        
    status = master_cpu.memory.memWrite(master_cpu.cores[core_id].value, adres=arg2, cpu_id=master_cpu.ID)
    if status == "STALL":
        target.fsm_state = 'EXECUTE'
        return
        
    target.fsm_state = 'FETCH'

def _h_stx(master_cpu, target, reg1, arg2):
    index_core = target.registers[0]
    data_core = target.registers[reg1]
    
    if (index_core is not None and master_cpu.cores[index_core].coreStatus == 'VALID' and
        data_core is not None and master_cpu.cores[data_core].coreStatus == 'VALID'):
        
        effective_addr = arg2 + master_cpu.cores[index_core].value
        status = master_cpu.memory.memWrite(master_cpu.cores[data_core].value, adres=effective_addr, cpu_id=master_cpu.ID)
        if status == "STALL":
            target.fsm_state = 'EXECUTE'
            return
        target.fsm_state = 'FETCH'
    else:
        target.fsm_state = 'EXECUTE'

# --- BRANCHING & CONTROL FLOW ---
def _h_halt(master_cpu, target, reg1, arg2):
    target.fsm_state = 'HALT'

def _h_suspend(master_cpu, target, reg1, arg2):
    target.fsm_state = 'WAIT_FOR_WORK'

def _h_jmp(master_cpu, target, reg1, arg2):
    target.PC = arg2
    target.fsm_state = 'FETCH'

def _h_jmpt(master_cpu, target, reg1, arg2):
    if target.last_test_core is None:
        raise RuntimeError("Hardware Fault: JMPT zonder voorafgaande TSTE!")
        
    test_core = master_cpu.cores[target.last_test_core]
    if test_core.coreStatus == 'WORKING':
        target.fsm_state = 'EXECUTE'
        return
        
    if test_core.status is True:
        target.PC = arg2
    target.fsm_state = 'FETCH'

def _h_jmpf(master_cpu, target, reg1, arg2):
    if target.last_test_core is None:
        raise RuntimeError("Hardware Fault: JMPF zonder voorafgaande TSTE!")
        
    test_core = master_cpu.cores[target.last_test_core]
    if test_core.coreStatus == 'WORKING':
        target.fsm_state = 'EXECUTE'
        return
        
    if test_core.status is False:
        target.PC = arg2
    target.fsm_state = 'FETCH'

def _h_succes(master_cpu, target, reg1, arg2):
    if target.status:
        target.PC = arg2
    target.fsm_state = 'FETCH'

def _h_fail(master_cpu, target, reg1, arg2):
    if not target.status:
        target.PC = arg2
    target.fsm_state = 'FETCH'

# --- THREADING, MULTI-CORE & CLUSTER CONTROL ---
def _h_context(master_cpu, target, reg1, arg2):
    if target != master_cpu:
        raise RuntimeError("Hardware Fault: Een sub-context probeerde zelf een CONTEXT te spawnen!")
    
    src_core_id = target.registers[reg1]
    if src_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
    
    core_src = master_cpu.cores[src_core_id]
    if core_src.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    # Check high-watermark
    if len(master_cpu.free_cores) < 15:
        target.status = 0
        target.fsm_state = 'FETCH'
        return

    parent_cpu_id = getattr(target, 'parent_cpu_id', getattr(target, 'ID', 0))
    nieuwe_ctx = HardwareContext(master_cpu, reg1, parent_cpu_id=parent_cpu_id)
    nieuwe_ctx.PC = arg2
    nieuwe_ctx.fsm_state = 'FETCH'
    
    master_cpu.contexts.append(nieuwe_ctx)
    target.status = 1
    target.fsm_state = 'FETCH'

def _h_rcontext(master_cpu, target, reg1, arg2):
    src_core_id = target.registers[reg1]
    if src_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_src = master_cpu.cores[src_core_id]
    if core_src.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    ack = master_cpu.ciu.request_remote_context(arg2, reg1, core_src.value)
    target.status = 1 if ack else 0
    target.fsm_state = 'FETCH'

def _h_sync(master_cpu, target, reg1, arg2):
    if len(master_cpu.contexts) > 0:
        target.PC = arg2
        target.status = 0
    else:
        target.status = 1
    target.fsm_state = 'FETCH'

def _h_allsync(master_cpu, target, reg1, arg2):
    lokale_activiteit = len(master_cpu.contexts) > 0
    remote_activiteit = not master_cpu.ciu.are_all_neighbors_idle()

    if lokale_activiteit or remote_activiteit:
        target.PC = arg2
        target.status = 0
    else:
        target.status = 1
    target.fsm_state = 'FETCH'

def _h_rboot(master_cpu, target, reg1, arg2):
    core_id = target.registers[reg1]
    if core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_link = master_cpu.cores[core_id]
    if core_link.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    ack = master_cpu.ciu.send_boot_remote(core_link.value, arg2)
    target.status = 1 if ack else 0
    target.fsm_state = 'FETCH'

def _h_close(master_cpu, target, reg1, arg2):
    if target == master_cpu:
        raise RuntimeError("Hardware Fault: De master-CPU mag CLOSE niet aanroepen!")
        
    for reg_val in target.registers.values():
        if reg_val is not None:
            if master_cpu.cores[reg_val].coreStatus == 'WORKING':
                target.fsm_state = 'EXECUTE'
                return
                
    target.fsm_state = 'DONE'

def _h_autoclose(master_cpu, target, reg1, arg2):
    if target == master_cpu:
        raise RuntimeError("Hardware Fault: De master-CPU mag AUTOCLOSE niet aanroepen!")
        
    for core_id in target.registers.values():
        if core_id is not None:
            if master_cpu.cores[core_id].coreStatus == 'WORKING':
                target.fsm_state = 'EXECUTE'
                return
                
    for core_id in target.registers.values():
        if core_id is not None:
            master_cpu.cores[core_id].coreStatus = 'IDLE'

    target.fsm_state = 'HALT'
    if target in master_cpu.contexts:
        master_cpu.contexts.remove(target)

def _h_join(master_cpu, target, reg1, arg2):
    if target != master_cpu:
        raise RuntimeError("Hardware Fault: Een sub-context kan geen JOIN uitvoeren!")

    if not master_cpu.contexts:
        target.status = 0
        target.PC = arg2
        target.fsm_state = 'FETCH'
        return

    oudste_thread = master_cpu.contexts[0]
    if oudste_thread.fsm_state not in ['DONE', 'HALT', 'CLOSE']:
        target.status = 0
        target.PC = arg2
        target.fsm_state = 'FETCH'
        return

    thread_result_core = oudste_thread.registers.get(reg1)
    if thread_result_core is None:
        raise RuntimeError(f"Hardware Fault: Thread reg {reg1} bevat geen uCore-pointer!")

    if master_cpu.cores[thread_result_core].coreStatus == 'WORKING':
        target.status = 0
        target.PC = arg2
        target.fsm_state = 'FETCH'
        return

    master_cpu.registers[reg1] = thread_result_core
    for reg_idx, core_id in oudste_thread.registers.items():
        if core_id is not None and core_id != thread_result_core:
            master_cpu.cores[core_id].coreStatus = 'IDLE'

    master_cpu.contexts.pop(0)
    target.status = 1
    target.fsm_state = 'FETCH'

# --- IO CONTROLLER HANDLERS ---
def _h_out(master_cpu, target, reg1, arg2):
    core_id = target.registers[reg1]
    if core_id is None:
        raise RuntimeError(f"Hardware Fault: OUT gebruikt leeg register R{reg1}!")
    if master_cpu.cores[core_id].coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return
        
    if master_cpu.io_bus is not None:
        success = master_cpu.io_bus.cpu_out(reg_num=arg2, value=master_cpu.cores[core_id].value)
        if not success:
            target.fsm_state = 'EXECUTE'
            return
    else:
        raise RuntimeError("Hardware Fault: OUT uitgevoerd maar geen IO-bus gekoppeld!")
        
    target.fsm_state = 'FETCH'

def _h_in(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
        
    if master_cpu.io_bus is not None:
        io_value = master_cpu.io_bus.cpu_in(reg_num=arg2)
        core_id = master_cpu.free_cores.popleft()
        master_cpu.cores[core_id].transfer = io_value
        master_cpu.cores[core_id].dispatch('ldv')
        target.registers[reg1] = core_id
        target.fsm_state = 'FETCH'
    else:
        raise RuntimeError("Hardware Fault: IN uitgevoerd maar geen IO-bus gekoppeld!")

def _h_iosync(master_cpu, target, reg1, arg2):
    if master_cpu.io_bus is not None:
        master_cpu.io_bus.cpu_iosync()
    else:
        raise RuntimeError("Hardware Fault: IOSYNC uitgevoerd maar geen IO-bus gekoppeld!")
    target.fsm_state = 'FETCH'

# --- CIU MAILBOX HANDLERS ---
# def _h_msg_start(master_cpu, target, reg1, arg2):
#     rx_core_id = target.registers[reg1]
#     ry_core_id = target.registers[arg2]
#     if rx_core_id is None or ry_core_id is None:
#         target.fsm_state = 'EXECUTE'
#         return
        
#     core_rx = master_cpu.cores[rx_core_id]
#     core_ry = master_cpu.cores[ry_core_id]
#     if core_rx.coreStatus != 'VALID' or core_ry.coreStatus != 'VALID':
#         target.fsm_state = 'EXECUTE'
#         return
        
#     if not master_cpu.free_cores:
#         target.fsm_state = 'EXECUTE'
#         return

#     parent_id = getattr(target, 'parent_cpu_id', getattr(target, 'parent_id', getattr(master_cpu, 'parent_id', 0)))
#     success, tx_id = master_cpu.ciu.msg_start(core_rx.value, core_ry.value, parent_id)
#     target.status = 1 if success else 0

#     if success:
#         core_id = master_cpu.free_cores.popleft()
#         master_cpu.cores[core_id].transfer = tx_id
#         master_cpu.cores[core_id].dispatch('ldv')
#         target.registers[arg2] = core_id
#     target.fsm_state = 'FETCH'
def _h_msg_start(master_cpu, target, reg1, arg2):
    rx_core_id = target.registers[reg1]
    ry_core_id = target.registers[arg2]
    
    if rx_core_id is None or ry_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_rx = master_cpu.cores[rx_core_id]
    core_ry = master_cpu.cores[ry_core_id]
    
    if core_rx.coreStatus != 'VALID' or core_ry.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return
        
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return

    parent_id = getattr(target, 'parent_cpu_id', getattr(target, 'parent_id', getattr(master_cpu, 'parent_id', 0)))
    
    # Probeer bericht te starten via de CIU
    success, tx_id = master_cpu.ciu.msg_start(core_rx.value, core_ry.value, parent_id)
    
    # --- NIEUW: STALL BIJ FULL FIFO (FLOW CONTROL) ---
    if not success:
        target.fsm_state = 'EXECUTE'  # Buurman FIFO is vol: Blijf in EXECUTE en probeer volgende tick opnieuw!
        return

    target.status = 1

    core_id = master_cpu.free_cores.popleft()
    master_cpu.cores[core_id].transfer = tx_id
    master_cpu.cores[core_id].dispatch('ldv')
    target.registers[arg2] = core_id
    target.fsm_state = 'FETCH'

def _h_msg_write(master_cpu, target, reg1, arg2):
    ry_core_id = target.registers[reg1]
    rx_core_id = target.registers[arg2]
    if ry_core_id is None or rx_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_ry = master_cpu.cores[ry_core_id]
    core_rx = master_cpu.cores[rx_core_id]
    if core_ry.coreStatus != 'VALID' or core_rx.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    success = master_cpu.ciu.msg_write(core_ry.value, core_rx.value)
    target.status = 1 if success else 0
    target.fsm_state = 'FETCH'

def _h_msg_done(master_cpu, target, reg1, arg2):
    ry_core_id = target.registers[reg1]
    if ry_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_ry = master_cpu.cores[ry_core_id]
    if core_ry.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    success = master_cpu.ciu.msg_done(core_ry.value)
    target.status = 1 if success else 0
    target.fsm_state = 'FETCH'

def _h_msg_open(master_cpu, target, reg1, arg2):
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return
        
    success, rx_id = master_cpu.ciu.msg_open()
    target.status = 1 if success else 0

    if success:
        core_id = master_cpu.free_cores.popleft()
        master_cpu.cores[core_id].transfer = rx_id
        master_cpu.cores[core_id].dispatch('ldv')
        target.registers[reg1] = core_id
    target.fsm_state = 'FETCH'

def _h_msg_probe(master_cpu, target, reg1, arg2):
    rx_core_id = target.registers[reg1]
    if rx_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_rx = master_cpu.cores[rx_core_id]
    if core_rx.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    match = master_cpu.ciu.msg_probe(core_rx.value)
    target.status = 1 if match else 0
    target.fsm_state = 'FETCH'

def _h_msg_read(master_cpu, target, reg1, arg2):
    ry_core_id = target.registers[reg1]
    if ry_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_ry = master_cpu.cores[ry_core_id]
    if core_ry.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return
        
    if not master_cpu.free_cores:
        target.fsm_state = 'EXECUTE'
        return

    success, data_val = master_cpu.ciu.msg_read(core_ry.value)
    target.status = 1 if success else 0

    if success:
        core_id = master_cpu.free_cores.popleft()
        master_cpu.cores[core_id].transfer = data_val
        master_cpu.cores[core_id].dispatch('ldv')
        target.registers[arg2] = core_id
    target.fsm_state = 'FETCH'

def _h_msg_close(master_cpu, target, reg1, arg2):
    ry_core_id = target.registers[reg1]
    if ry_core_id is None:
        target.fsm_state = 'EXECUTE'
        return
        
    core_ry = master_cpu.cores[ry_core_id]
    if core_ry.coreStatus != 'VALID':
        target.fsm_state = 'EXECUTE'
        return

    success = master_cpu.ciu.msg_close(core_ry.value)
    target.status = 1 if success else 0
    target.fsm_state = 'FETCH'


# =========================================================================
# DISPATCH TABLE MAPPING (O(1) INSTRUCTIE EXECUTIE TABLE)
# =========================================================================

EXEC_DISPATCH = {
    # Compute & Load
    Op.LDI: _h_ldi,       Op.LD: _h_ld,         Op.CPUID: _h_cpu_id,  Op.PID: _h_pid,
    Op.LDM: _h_ldm,       Op.LDX: _h_ldx,
    
    # Arithmetic
    Op.ADD: _h_add,       Op.SUB: _h_sub,       Op.MUL: _h_mul,       Op.DIV: _h_div,
    Op.ADDI: _h_addi,     Op.SUBI: _h_subi,     Op.MULI: _h_muli,     Op.DIVI: _h_divi,
    Op.INC: _h_inc,       Op.DEC: _h_dec,       Op.MOD: _h_mod,       Op.XOR: _h_xor,
    Op.SHIFTL: _h_shiftl, Op.SHIFTR: _h_shiftr, Op.SM32_RND: _h_sm32_rnd, Op.ROTL32: _h_rotl32,

    # Comparisons & Test
    Op.TST: _h_tst,       Op.TSTE: _h_tste,     Op.TSTG: _h_tstg,     Op.TSTZ: _h_tstz,

    # Memory Store
    Op.STO: _h_sto,       Op.STX: _h_stx,

    # Control Flow & Branching
    Op.HALT: _h_halt,     Op.SUSPEND: _h_suspend, Op.JMP: _h_jmp,
    Op.JMPT: _h_jmpt,     Op.JMPF: _h_jmpf,     Op.SUCCES: _h_succes, Op.FAIL: _h_fail,

    # Threading, Multi-Core & Parallelism
    Op.CONTEXT: _h_context,   Op.RCONTEXT: _h_rcontext, Op.SYNC: _h_sync,
    Op.ALLSYNC: _h_allsync,   Op.RBOOT: _h_rboot,       Op.CLOSE: _h_close,
    Op.AUTOCLOSE: _h_autoclose, Op.JOIN: _h_join,

    # I/O Bus
    Op.OUT: _h_out,       Op.IN: _h_in,         Op.IOSYNC: _h_iosync,

    # CIU Mailbox
    Op.MSG_START: _h_msg_start, Op.MSG_WRITE: _h_msg_write, Op.MSG_DONE: _h_msg_done,
    Op.MSG_OPEN: _h_msg_open,   Op.MSG_PROBE: _h_msg_probe, Op.MSG_READ: _h_msg_read,
    Op.MSG_CLOSE: _h_msg_close,
}


# =========================================================================
# HOOFD EXECUTION CYCLE (STATE MACHINE)
# =========================================================================

def _execute_cycleZ32(master_cpu, target):
    if target.fsm_state == 'FETCH':
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
            target.decoded_reg1 = payload % 10  
            target.decoded_arg2 = payload // 10 
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

        handler = EXEC_DISPATCH.get(opcode)
        if handler:
            handler(master_cpu, target, reg1, arg2)
        else:
            raise RuntimeError(f"Hardware Error: Geen handler gedefinieerd voor opcode {opcode}")