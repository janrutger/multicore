# main.py
# main.py
import time  # <--- NIEUW: Nodig voor de wall-clock metingen!
from InmosZ32 import CPU
from opcodes import Op, Reg, assembly_program, encrypt_program, context_test, context_test1, context_stress
from assembler import assemble
from frontpanel import FrontPanel

def run_test():
    print("--- START CPU MATRIX SIMULATIE ---")
    
    cpu = CPU()
    # --- CONFIGURATIE VLAG ---
    SHOW_GUI = True  # Zet op False om de GUI volledig uit te schakelen voor maximale performance!
    # Initialiseer het frontpaneel als de vlag aan staat
    panel = FrontPanel(num_cores=32) if SHOW_GUI else None

    # De assembler doet nu al het rekenwerk voor je!
    test_program = assemble(context_stress)  
    
    # Print even ter controle de gegenereerde machinecode integers
    print(f"Gegenereerde machinecode: {test_program}\n")

    # Laad het programma in het geheugen
    for adres, machine_woord in enumerate(test_program):
        cpu.memory.memWrite(machine_woord, adres)

    # --- INITIALISEER TIJD-METERS ---
    totale_gui_tijd = 0.0
    start_simulatie = time.perf_counter()  # Start de totale stopwatch
    # --------------------------------

    # Start de klok-lus (Clock Cycles)
    max_ticks = 1000000  
    for tick_count in range(1, max_ticks + 1):
        current_state = cpu.fsm_state
        current_pc = cpu.PC
        
        # Geef het hele systeem één kloktick
        cpu.tick()


        # --- PARSE EN MEET OVERHEAD FRONT-PANEL ---
        # We starten de stopwatch nét alle overhead voor reporting wordt 
        # (zoals je expliciet aangaf) keurig meegeteld als GUI-overhead!
        start_gui_check = time.perf_counter()

        # 1. Bouw de status-regel voor de Master-CPU
        master_log = f"Tick {tick_count:02d} | MASTER -> State: {cpu.fsm_state:<7} | PC: {cpu.PC:<2} | MIR: {cpu.MIR if cpu.MIR is not None else 'None':<12}"
        
        # 2. Bouw de status-regel voor eventuele actieve sub-threads (contexts)
        context_logs = []
        for idx, ctx in enumerate(cpu.contexts):
            context_logs.append(f"   [Thread {idx}] State: {ctx.fsm_state:<7} | PC: {ctx.PC:<2} | MIR: {ctx.MIR if ctx.MIR is not None else 'None':<12}")
        
        # 3. Print alles netjes onder elkaar
        print(master_log)
        for c_log in context_logs:
            print(c_log)

        # # --- PARSE EN MEET OVERHEAD FRONT-PANEL ---
        # # We starten de stopwatch nét voor de 'if' zodat het 'tijdsverlies van de if' 
        # # (zoals je expliciet aangaf) keurig wordt meegeteld als GUI-overhead!
        # start_gui_check = time.perf_counter()
        
        if SHOW_GUI and panel:
            panel.update_cores(cpu.cores)

        eind_gui_check = time.perf_counter()
        totale_gui_tijd += (eind_gui_check - start_gui_check)
        # ------------------------------------------

        # Vraag aan de CPU of het hele systeem nu echt stroomloos kan
        if cpu.is_completely_idle():
            print(f"\n[SYSTEM] Volledige HALT bereikt in tick {tick_count}! Alle cores zijn uitgeraasd.")
            break

    # --- BEREKEN WALL-CLOCK PERFORMANCE ---
    eind_simulatie = time.perf_counter()
    bruto_runtime = eind_simulatie - start_simulatie
    netto_core_runtime = bruto_runtime - totale_gui_tijd
    # --------------------------------------

    # --- GEAVANCEERD MATRIX STATUS RAPPORT ---
    print("\033[92m\n==========================================================")
    print("                EINDSTATUS STERN MATRIX                   ")
    print("==========================================================")
    print(f"Vrije Cores over in wachtrij ({len(cpu.free_cores)}/32):\n {list(cpu.free_cores)}")
    print("----------------------------------------------------------")
    print(f"{'Core':<6} | {'Status':<8} | {'Waarde':<8} | {'Gekoppeld Register':<20}")
    print("----------------------------------------------------------")
    
    reg_names = {0: "I (R0)", 1: "A (R1)", 2: "B (R2)", 3: "C (R3)", 4: "K (R4)", 
                 5: "L (R5)", 6: "M (R6)", 7: "X (R7)", 8: "Y (R8)", 9: "Z (R9)"}
    
    core_to_reg = {}
    for reg_id, core_id in cpu.registers.items():
        if core_id is not None:
            naam = reg_names.get(reg_id, f"R{reg_id}")
            core_to_reg[core_id] = f"Register {naam}"
            
    if cpu.last_test_core is not None:
        if cpu.last_test_core in core_to_reg:
            core_to_reg[cpu.last_test_core] += " + Status (last_test)"
        else:
            core_to_reg[cpu.last_test_core] = "Status (last_test)"
            
    for c_id, core in enumerate(cpu.cores):
        status = core.coreStatus
        val = core.value
        reg_naam = core_to_reg.get(c_id, "-")
        
        if reg_naam != "-":
            print(f"Core {c_id:<2} | {status:<8} | {val:>10} | <-- {reg_naam}")
        else:
            print(f"Core {c_id:<2} | {status:<8} | {val:>10} | {reg_naam}")
            
    print("==========================================================\n")
    
    # === GEHEUGEN DUMP ===
    print("==========================================================")
    print("             GEHEUGEN DUMP (Adres 512 t/m )            ")
    print("==========================================================")
    
    start_adres = 512
    aantal_adressen = 50
    
    for i in range(aantal_adressen):
        current_addr = start_adres + i
        waarde = cpu.memory.memRead(current_addr)
        
        if 32 <= waarde <= 126:
            char_repr = f"'{chr(waarde)}'"
        else:
            char_repr = "???"
            
        label = " <-- Master Key (M)" if current_addr == 512 else ""
        print(f"Adres {current_addr:<3} | Waarde: {waarde:>10} | Karakter: {char_repr:<5}{label}")
        
    print("==========================================================\n")


    # === GEOPTIMALISEERD: HET METRIC PERFORMANCE RAPPORT (INCLUSIEF HW ESTIMATE) ===
    netto_ticks_per_sec = tick_count / netto_core_runtime
    aantal_cores = len(cpu.cores)
    hardware_equivalent_hz = netto_ticks_per_sec * aantal_cores
    
    print("==========================================================")
    print("             WALL-CLOCK PERFORMANCE RAPPORT               ")
    print("==========================================================")
    print(f" Totale CPU Ticks verwerkt : {tick_count} Ticks")
    print(f" Bruto Looptijd Script     : {bruto_runtime:.6f} seconden")
    print(f" Geregistreerde GUI-aftrek : {totale_gui_tijd:.6f} seconden (incl. Overhead)")
    print(f" NETTO MATRIX RUNTIME      : {netto_core_runtime:.6f} seconden")
    print(f" Netto Snelheid Simulator  : {netto_ticks_per_sec:.2f} Ticks/sec (Hz)")
    print("----------------------------------------------------------")
    print(f" ECHTE PARALLELLE HARDWARE SCHATING (Pure Silicium Throughput):")
    print(f" Gecorrigeerd voor         : {aantal_cores} Cores werkend op één klokflank")
    if hardware_equivalent_hz >= 1000000:
        print(f" Geschatte HW Kloksnelheid : {(hardware_equivalent_hz / 1000000):.3f} MHz 🔥")
    else:
        print(f" Geschatte HW Kloksnelheid : {(hardware_equivalent_hz / 1000):.2f} kHz 🔥")
    print("==========================================================\033[0m\n")

    if SHOW_GUI and panel:
        print("\nSluit het frontpaneel-venster om de simulatie te beëindigen.")
        panel.root.mainloop() 

if __name__ == "__main__":
    run_test()




# from InmosZ32 import CPU
# from opcodes import Op, Reg, assembly_program, encrypt_program, context_test, context_test1, context_stress
# from assembler import assemble
# from frontpanel import FrontPanel

# def run_test():
#     print("--- START CPU MATRIX SIMULATIE ---")
    
#     cpu = CPU()
#     # --- CONFIGURATIE VLAG ---
#     SHOW_GUI = True  # Zet op False om de GUI volledig uit te schakelen voor maximale performance!
#     # Initialiseer het frontpaneel als de vlag aan staat
#     panel = FrontPanel(num_cores=32) if SHOW_GUI else None


#     # De assembler doet nu al het rekenwerk voor je!
#     # test_program = assemble(encrypt_program)        # the source can be found in opcodes.py
#     test_program = assemble(context_stress)  
    
#     # Print even ter controle de gegenereerde machinecode integers
#     print(f"Gegenereerde machinecode: {test_program}\n")

#     # Laad het programma in het geheugen
#     for adres, machine_woord in enumerate(test_program):
#         cpu.memory.memWrite(machine_woord, adres)



#     # Start de klok-lus (Clock Cycles)
#     max_ticks = 1000000  # We kunnen dit nu gerust hoger zetten als veiligheidsmarge
#     for tick_count in range(1, max_ticks + 1):
#         current_state = cpu.fsm_state
#         current_pc = cpu.PC
        
#         # Geef het hele systeem één kloktick
#         cpu.tick()

#         # Print de status van deze specifieke tick
#         # print(f"Tick {tick_count:02d} | CPU State: {current_state:<7} | PC: {current_pc} | MIR: {cpu.MIR}")
#         # --- DE NIEUWE PARALLELLE LOGGING ---
#         # 1. Bouw de status-regel voor de Master-CPU
#         master_log = f"Tick {tick_count:02d} | MASTER -> State: {cpu.fsm_state:<7} | PC: {cpu.PC:<2} | MIR: {cpu.MIR if cpu.MIR is not None else 'None':<12}"
        
#         # 2. Bouw de status-regel voor eventuele actieve sub-threads (contexts)
#         context_logs = []
#         for idx, ctx in enumerate(cpu.contexts):
#             context_logs.append(f"   [Thread {idx}] State: {ctx.fsm_state:<7} | PC: {ctx.PC:<2} | MIR: {ctx.MIR if ctx.MIR is not None else 'None':<12}")
        
#         # 3. Print alles netjes onder elkaar
#         print(master_log)
#         for c_log in context_logs:
#             print(c_log)

#         # Update het frontpaneel in realtime tijdens de simulatie-lus
#         if SHOW_GUI and panel:
#             panel.update_cores(cpu.cores)

#         # NIEUW: Vraag aan de CPU of het hele systeem (CPU + Cores) nu echt stroomloos kan
#         if cpu.is_completely_idle():
#             print(f"\n[SYSTEM] Volledige HALT bereikt in tick {tick_count}! Alle cores zijn uitgeraasd.")
#             break

    

#     # --- GEAVANCEERD MATRIX STATUS RAPPORT ---
#     print("\n==========================================================")
#     print("                EINDSTATUS STERN MATRIX                   ")
#     print("==========================================================")
#     print(f"Vrije Cores over in wachtrij ({len(cpu.free_cores)}/32):\n {list(cpu.free_cores)}")
#     print("----------------------------------------------------------")
#     print(f"{'Core':<6} | {'Status':<8} | {'Waarde':<8} | {'Gekoppeld Register':<20}")
#     print("----------------------------------------------------------")
    
    
#     # Maak een handige omgekeerde mapping van Core-ID naar Registernaam.
#     # We mappen de bekende integers (0 t/m 9) naar hun STERN-registernaam.
#     reg_names = {0: "I (R0)", 1: "A (R1)", 2: "B (R2)", 3: "C (R3)", 4: "K (R4)", 
#                  5: "L (R5)", 6: "M (R6)", 7: "X (R7)", 8: "Y (R8)", 9: "Z (R9)"}
    
#     core_to_reg = {}
#     for reg_id, core_id in cpu.registers.items():
#         if core_id is not None:
#             # Haal de mooie naam op, of val terug op het ID als het onbekend is
#             naam = reg_names.get(reg_id, f"R{reg_id}")
#             core_to_reg[core_id] = f"Register {naam}"
            
#     # Voeg de last_test_core (Status) apart toe als die er is
#     if cpu.last_test_core is not None:
#         if cpu.last_test_core in core_to_reg:
#             core_to_reg[cpu.last_test_core] += " + Status (last_test)"
#         else:
#             core_to_reg[cpu.last_test_core] = "Status (last_test)"
            

#     # Loop door alle 32 cores van de matrix heen
#     for c_id, core in enumerate(cpu.cores):
#         status = core.coreStatus
#         val = core.value
#         reg_naam = core_to_reg.get(c_id, "-")
        
#         # Geef de actieve/valid registers een opvallend vlaggetje in de log
#         if reg_naam != "-":
#             print(f"Core {c_id:<2} | {status:<8} | {val:>10} | <-- {reg_naam}")
#         else:
#             print(f"Core {c_id:<2} | {status:<8} | {val:>10} | {reg_naam}")
            
#     print("==========================================================\n")

    
#     # === NIEUW: Print de databuffer vanaf 512 (Masterkey + Encrypted String) ===
#     # === GEHEUGEN DUMP (Consistent vanaf 512 voor 24 adressen) ===
#     print("==========================================================")
#     print("             GEHEUGEN DUMP (Adres 512 t/m )            ")
#     print("==========================================================")
    
#     start_adres = 512
#     aantal_adressen = 50
    
#     for i in range(aantal_adressen):
#         current_addr = start_adres + i
#         waarde = cpu.memory.memRead(current_addr)
        
#         # Vertaal ALTIJD naar een karakter als het binnen de leesbare ASCII-reeks valt
#         if 32 <= waarde <= 126:
#             char_repr = f"'{chr(waarde)}'"
#         else:
#             char_repr = "???"
            
#         # Voeg alleen het specifieke label toe voor de Master Key op het startadres
#         label = " <-- Master Key (M)" if current_addr == 512 else ""
        
#         print(f"Adres {current_addr:<3} | Waarde: {waarde:>10} | Karakter: {char_repr:<5}{label}")
        
#     print("==========================================================\n")


#      # Nette afsluiting van het venster na de HALT
#     if SHOW_GUI and panel:
#         print("\nSluit het frontpaneel-venster om de simulatie te beëindigen.")
#         panel.root.mainloop() # Houdt het venster open zodat je het eindresultaat kunt bewonderen

# if __name__ == "__main__":
#     run_test()