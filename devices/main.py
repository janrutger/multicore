# main.py
from cpu import CPU
from opcodes import Op, Reg
from assembler import assemble
from frontpanel import FrontPanel

def run_test():
    print("--- START CPU MATRIX SIMULATIE ---")
    
    cpu = CPU()
    # --- CONFIGURATIE VLAG ---
    SHOW_GUI = True  # Zet op False om de GUI volledig uit te schakelen voor maximale performance!
    # Initialiseer het frontpaneel als de vlag aan staat
    panel = FrontPanel(num_cores=16) if SHOW_GUI else None

    # Je volledige programma, nu super leesbaar met labels!
    # assembly_program = """
    # LDI  A, 0        ; Laad accumulator A met 42
    # LDI  B, 100      ; Laad register B met 42
    # LDI  C, 1
    # TEST:
    #     TSTE A, B          ; Vergelijk Register A en Register B
    #     JMPT END_IF      ; Spring naar de ELSE-tak als uitkomst False is
    
    #     ADD A, C     ; ELSE-tak: Zet A op 11
    #     JMP TEST
        
    # END_IF:
    #     LDI A, 99
    #     STO  A, 100    ; Sla de uiteindelijke waarde van A op op RAM-adres 100
    #     HALT           ; Einde van de simulatie
    # """
    # assembly_program = """ 
    #     LDI A -42         ; Activeert een core om A = 4 te maken
    #     LDI B 4200        ; Activeert een core om B = 3 te maken
    #     MUL A B         ; CPU delegeert 'slow_mul' aan een nieuwe core met arg1=Core_A en arg2=Core_B
    #     STO A 100       ; CPU stalled tot de MUL core VALID is, en schrijft 12 naar adres 50
    #     HALT 
    # """
    assembly_program = """ 
        ; --- INITIALISATIE ---
        LDI A 0            ; Register A = Onze loop-counter (start op 0)
        LDI B 100            ; Register B = De doelwaarde van de counter (3)
        LDI C 1            ; Register C = De stapgrootte (+1 per ronde)
        LDI X 0            ; Register X = De totale som-accumulator (start op 0)
        LDI Y 5            ; Register Y = De vaste waarde die we telkens vermenigvuldigen (5)

    LOOP:
        ; --- TEST LUSCONDITIE ---
        TSTE A B           ; Vergelijk counter (A) met doelwaarde 3 (B)
        JMPT END_LOOP      ; Als A == 3 (True), spring uit de lus naar END_LOOP

        ; --- BEREKENING ---
        MUL Y A            ; Activeer core voor Y * A (de huidige stap)
        ADD X Y            ; CPU stalled tot de MUL core VALID is, en telt op bij X

        ; --- TELLER OPHOGEN ---
        ADD A C            ; A = A + 1 (Verhoog counter)

        ; --- REFRESH INVOER ---
        LDI Y 5            ; Overschrijf register Y met de schone waarde 5
                           ; om te voorkomen dat het oude Core-ID als invoer dient

        JMP LOOP           ; Spring onvoorwaardelijk terug naar de start van de lus

    END_LOOP:
        ; --- AFRASTING EN OPSLAG ---
        STO X 100          ; Sla de totale som (X) op op RAM-adres 100
        HALT               ; Sluit de simulatie af
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

    # NIEUW: Lees de permanent opgeslagen waarde uit het RAM-geheugen op adres 100
    ram_value_100 = cpu.memory.memRead(100)
    print(f"-> RAM OPBESLAG (Adres 100): {ram_value_100} (Verwacht na STO: 99)")


     # Nette afsluiting van het venster na de HALT
    if SHOW_GUI and panel:
        print("\nSluit het frontpaneel-venster om de simulatie te beëindigen.")
        panel.root.mainloop() # Houdt het venster open zodat je het eindresultaat kunt bewonderen

if __name__ == "__main__":
    run_test()