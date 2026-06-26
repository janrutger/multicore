# main.py
from cpu import CPU
from opcodes import Op, Reg, assembly_program, encrypt_program
from assembler import assemble
from frontpanel import FrontPanel

def run_test():
    print("--- START CPU MATRIX SIMULATIE ---")
    
    cpu = CPU()
    # --- CONFIGURATIE VLAG ---
    SHOW_GUI = True  # Zet op False om de GUI volledig uit te schakelen voor maximale performance!
    # Initialiseer het frontpaneel als de vlag aan staat
    panel = FrontPanel(num_cores=16) if SHOW_GUI else None


    # De assembler doet nu al het rekenwerk voor je!
    test_program = assemble(encrypt_program)        # the source can be found in opcodes.py
    
    # Print even ter controle de gegenereerde machinecode integers
    print(f"Gegenereerde machinecode: {test_program}\n")

    # Laad het programma in het geheugen
    for adres, machine_woord in enumerate(test_program):
        cpu.memory.memWrite(machine_woord, adres)



    # Start de klok-lus (Clock Cycles)
    max_ticks = 1000000  # We kunnen dit nu gerust hoger zetten als veiligheidsmarge
    for tick_count in range(1, max_ticks + 1):
        current_state = cpu.cpu_state
        current_pc = cpu.PC
        
        # Geef het hele systeem één kloktick
        cpu.tick()

        # Print de status van deze specifieke tick
        print(f"Tick {tick_count:02d} | CPU State: {current_state:<7} | PC: {current_pc} | MIR: {cpu.MIR}")

        # NIEUW: Update het frontpaneel in realtime tijdens de simulatie-lus
        if SHOW_GUI and panel:
            panel.update_cores(cpu.cores)

        # NIEUW: Vraag aan de CPU of het hele systeem (CPU + Cores) nu echt stroomloos kan
        if cpu.is_completely_idle():
            print(f"\n[SYSTEM] Volledige HALT bereikt in tick {tick_count}! Alle cores zijn uitgeraasd.")
            break

    

    # --- GEAVANCEERD MATRIX STATUS RAPPORT ---
    print("\n==========================================================")
    print("                EINDSTATUS STERN MATRIX                   ")
    print("==========================================================")
    print(f"Vrije Cores over in wachtrij ({len(cpu.free_cores)}/16):\n {list(cpu.free_cores)}")
    print("----------------------------------------------------------")
    print(f"{'Core':<6} | {'Status':<8} | {'Waarde':<8} | {'Gekoppeld Register':<20}")
    print("----------------------------------------------------------")
    
    
    # Maak een handige omgekeerde mapping van Core-ID naar Registernaam.
    # We mappen de bekende integers (0 t/m 9) naar hun STERN-registernaam.
    reg_names = {0: "I (R0)", 1: "A (R1)", 2: "B (R2)", 3: "C (R3)", 4: "K (R4)", 
                 5: "L (R5)", 6: "M (R6)", 7: "X (R7)", 8: "Y (R8)", 9: "Z (R9)"}
    
    core_to_reg = {}
    for reg_id, core_id in cpu.registers.items():
        if core_id is not None:
            # Haal de mooie naam op, of val terug op het ID als het onbekend is
            naam = reg_names.get(reg_id, f"R{reg_id}")
            core_to_reg[core_id] = f"Register {naam}"
            
    # Voeg de last_test_core (Status) apart toe als die er is
    if cpu.last_test_core is not None:
        if cpu.last_test_core in core_to_reg:
            core_to_reg[cpu.last_test_core] += " + Status (last_test)"
        else:
            core_to_reg[cpu.last_test_core] = "Status (last_test)"
            

    # Loop door alle 16 cores van de matrix heen
    for c_id, core in enumerate(cpu.cores):
        status = core.coreStatus
        val = core.value
        reg_naam = core_to_reg.get(c_id, "-")
        
        # Geef de actieve/valid registers een opvallend vlaggetje in de log
        if reg_naam != "-":
            print(f"Core {c_id:<2} | {status:<8} | {val:<8} | <-- {reg_naam}")
        else:
            print(f"Core {c_id:<2} | {status:<8} | {val:<8} | {reg_naam}")
            
    print("==========================================================\n")

    
    # === NIEUW: Print de databuffer vanaf 512 (Masterkey + Encrypted String) ===
    # === GEHEUGEN DUMP (Consistent vanaf 512 voor 24 adressen) ===
    print("==========================================================")
    print("             GEHEUGEN DUMP (Adres 512 t/m 535)            ")
    print("==========================================================")
    
    start_adres = 512
    aantal_adressen = 24
    
    for i in range(aantal_adressen):
        current_addr = start_adres + i
        waarde = cpu.memory.memRead(current_addr)
        
        # Vertaal ALTIJD naar een karakter als het binnen de leesbare ASCII-reeks valt
        if 32 <= waarde <= 126:
            char_repr = f"'{chr(waarde)}'"
        else:
            char_repr = "???"
            
        # Voeg alleen het specifieke label toe voor de Master Key op het startadres
        label = " <-- Master Key (M)" if current_addr == 512 else ""
        
        print(f"Adres {current_addr:<3} | Waarde: {waarde:<5} | Karakter: {char_repr:<5}{label}")
        
    print("==========================================================\n")


     # Nette afsluiting van het venster na de HALT
    if SHOW_GUI and panel:
        print("\nSluit het frontpaneel-venster om de simulatie te beëindigen.")
        panel.root.mainloop() # Houdt het venster open zodat je het eindresultaat kunt bewonderen

if __name__ == "__main__":
    run_test()