# --- MSG INSTRUCTIE AFHANDELING IN EXECUTELUS ---

if instr == "MSG_START":
    tag_val = target.registers.get(rx_reg, 0)
    size_val = target.registers.get(ry_reg, 0)
    parent_id = getattr(target, 'parent_cpu_id', None)
    if parent_id is None:
        parent_id = getattr(master_cpu, 'parent_id', 0)

    success, tx_id = master_cpu.ciu.msg_start(tag_val, size_val, parent_id)
    target.status = 1 if success else 0
    if success:
        target.registers[out_reg] = tx_id

elif instr == "MSG_WRITE":
    tx_id = target.registers.get(ry_reg, 0)
    data_val = target.registers.get(rx_reg, 0)

    success = master_cpu.ciu.msg_write(tx_id, data_val)
    target.status = 1 if success else 0

elif instr == "MSG_DONE":
    tx_id = target.registers.get(ry_reg, 0)

    success = master_cpu.ciu.msg_done(tx_id)
    target.status = 1 if success else 0

elif instr == "MSG_OPEN":
    success, rx_id = master_cpu.ciu.msg_open()
    target.status = 1 if success else 0
    if success:
        target.registers[out_reg] = rx_id

elif instr == "MSG_PROBE":
    expected_tag = target.registers.get(rx_reg, 0)

    match = master_cpu.ciu.msg_probe(expected_tag)
    target.status = True if match else False

elif instr == "MSG_READ":
    rx_id = target.registers.get(ry_reg, 0)

    success, val = master_cpu.ciu.msg_read(rx_id)
    target.status = 1 if success else 0
    if success:
        target.registers[out_reg] = val

elif instr == "MSG_CLOSE":
    rx_id = target.registers.get(ry_reg, 0)

    success = master_cpu.ciu.msg_close(rx_id)
    target.status = 1 if success else 0

# --- CONTROL FLOW INSTRUCTIES ---

elif instr == "SUCCES":
    if target.status:
        target.PC = jump_pc

elif instr == "FAIL":
    if not target.status:
        target.PC = jump_pc