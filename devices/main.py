# main.py
from cpu import CPU
from opcodes import Op, Reg
from assembler import assemble

def run_test():
    print("--- START CPU MATRIX SIMULATIE ---")
    
    cpu = CPU()

    # Je volledige programma, nu super leesbaar met labels!
    assembly_program = """
    LDI  A, 42         ; Laad accumulator A met 42
    LDI  B, 42         ; Laad register B met 42
    TSTE A, B          ; Vergelijk Register A en Register B
    JMPF ELSE_TAK      ; Spring naar de ELSE-tak als uitkomst False is
    
    IF_TAK:
        LDI  A, 99     ; IF-tak: Zet A op 99
        JMP  END_IF    ; Spring over de else-tak heen naar de STO
        
    ELSE_TAK:
        LDI  A, 11     ; ELSE-tak: Zet A op 11
        
    END_IF:
        STO  A, 100    ; Sla de uiteindelijke waarde van A op op RAM-adres 100
        HALT           ; Einde van de simulatie
    """

    # De assembler doet nu al het rekenwerk voor je!
    test_program = assemble(assembly_program)
    
    # Print even ter controle de gegenereerde machinecode integers
    print(f"Gegenereerde machinecode: {test_program}\n")

    # Laad het programma in het geheugen
    for adres, machine_woord in enumerate(test_program):
        cpu.memory.memWrite(machine_woord, adres)

    # 3. Schrijf alvast een testwaarde op adres 20 voor de LDM instructie
    # LDM B 20 gaat deze 55 dus inlezen in Register B!
    cpu.memory.memWrite(55, adres=20)

    # 4. Start de klok-lus (Clock Cycles)
    max_ticks = 100  # We kunnen dit nu gerust hoger zetten als veiligheidsmarge
    for tick_count in range(1, max_ticks + 1):
        current_state = cpu.cpu_state
        current_pc = cpu.PC
        
        # Geef het hele systeem één kloktick
        cpu.tick()

        # Print de status van deze specifieke tick
        print(f"Tick {tick_count:02d} | CPU State: {current_state:<7} | PC: {current_pc} | MIR: {cpu.MIR}")

        # NIEUW: Vraag aan de CPU of het hele systeem (CPU + Cores) nu echt stroomloos kan
        if cpu.is_completely_idle():
            print(f"\n[SYSTEM] Volledige HALT bereikt in tick {tick_count}! Alle cores zijn uitgeraasd.")
            break

    # --- SIMULATIE RESULTATEN RAPPORT ---
    print("\n--- MATRIX STATUS RAPPORT ---")
    print(f"Vrije Cores over in wachtrij: {list(cpu.free_cores)}")
    print(f"Register I (R0) wijst naar Core-ID: {cpu.registers[Reg.I]}")
    print(f"Register A (R1) wijst naar Core-ID: {cpu.registers[Reg.A]}")
    print(f"Register B (R2) wijst naar Core-ID: {cpu.registers[Reg.B]}")
    print(f"Status register wijst naar Core-ID: {cpu.last_test_core}")
    
    # Haal de uitkomst op uit de core waar Register A (Reg.A = 1) nu naar wijst
    final_core_id = cpu.registers[Reg.A]
    if final_core_id is not None:
        final_value = cpu.cores[final_core_id].value
        print(f"-> EINDRESULTAAT in Core {final_core_id} (Register A): {final_value} (Verwacht: 99)")
    else:
        print("-> Fout: Register A heeft geen core toegewezen gekregen.")

    # NIEUW: Lees de permanent opgeslagen waarde uit het RAM-geheugen op adres 100
    ram_value_100 = cpu.memory.memRead(100)
    print(f"-> RAM OPBESLAG (Adres 100): {ram_value_100} (Verwacht na STO: 99)")

if __name__ == "__main__":
    run_test()