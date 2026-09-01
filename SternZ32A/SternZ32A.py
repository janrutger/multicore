# # SternZ32A.py

# import tkinter as tk
# import time
# import sys
# import os
# from InmosZ32A import CPU
# from opcodes import context_stress, display_test, encrypt_program
# from assemblerV2 import assemble
# from frontpanelZ32G import FrontPanel
# from IOcontroller import IOController  # Importeer de nieuwe IO-chip!


# class SternZ32Mainboard:
#     def __init__(self):
#         print("--- INITIALISEER STERN-Z32 PLATFORM (EVENT-DRIVEN) ---")
        
#         # 1. Start de Master GUI Root die het ritme en de venster-contexts bepaalt
#         self.root = tk.Tk()
#         self.root.title("STERN-Z32 Mainboard Central Clock")
#         self.root.configure(bg="#1e1e1e")
        
#         # 2. Initialiseer de CPU hardware matrix (32 cores + context switches)
#         self.cpu = CPU()
#         self.show_log = False
        
#         # 3. UPGRADE: Soldeer de IOController op het mainboard chipset-vlak
#         self.io_controller = IOController(self.root)

#         # Koppel de IO-controller ook direct aan de CPU
#         self.cpu.IO(self.io_controller)           # Solder jumper when the right CPU is installed
        
#         # 4. Koppel en bed (embed) het Frontpanel in deze root
#         self.panel = FrontPanel(self.root, num_cores=32)
        
#         # 5. NIEUW: Dynamisch firmware laden vanuit .bin of terugvallen op de default test_program
#         test_program = []
        
#         # Controleer of er een extern bestand is meegegeven via de command line
#         if len(sys.argv) > 1:
#             firmware_pad = sys.argv[1]
#             if os.path.exists(firmware_pad):
#                 print(f"Firmware gevonden! Laden van: {firmware_pad}")
#                 try:
#                     with open(firmware_pad, "r") as f:
#                         # Lees elke regel, strip whitespace en converteer naar integer
#                         test_program = [int(line.strip()) for line in f if line.strip()]
#                     print(f"Firmware succesvol geladen ({len(test_program)} instructies).")
#                 except ValueError as e:
#                     print(f"Fout tijdens parsen van {firmware_pad}. Is het bestand corrupt?", file=sys.stderr)
#                     sys.exit(1)
#             else:
#                 print(f"Fout: Opgegeven firmwarebestand '{firmware_pad}' niet gevonden!", file=sys.stderr)
#                 sys.exit(1)
#         else:
#             # Fallback op de klassieke ingebouwde assembler-methode als er geen argument is
#             print("Geen externe firmware opgegeven. Fallback naar ingebouwde 'context_stress'...")
#             test_program = assemble(encrypt_program)  
        
#         print(f"Gegenereerde/Geladen machinecode: {test_program}\n")
        
#         # for adres, machine_woord in enumerate(test_program):
#         #     self.cpu.memory.memWrite(machine_woord, adres)
#         self.cpu.memory.write_rom(test_program, start_adres=0)
            
#         # Systeemtellers & Performance Tuning
#         self.totale_ticks = 0
#         self.cycles_per_frame = 50  # Aantal CPU-ticks dat we per GUI-yield wegtikken

#     def start(self):
#         """Start de master clock van de emulator en geeft de controle over aan Tkinter"""
#         print("--- START CPU MATRIX + IO SIMULATIE ---")
#         self.start_tijd = time.perf_counter()
#         self.gameloop()
#         self.root.mainloop()  # De hoofd event-loop van Tkinter draait nu het systeem

#     def gameloop(self):
#         """De ononderbroken klok-trein (Heartbeat) van de Inmos-Z32 en IO-Controller"""
#         IO_PRESCALER = 5000  # Voer pas een I/O-tick uit om de 5000 CPU-clocks
#         # 1. Bestook de CPU en chipset met een batch kloktikken
#         for _ in range(self.cycles_per_frame):
#             if not self.cpu.is_completely_idle():
#                 # Voer de werkelijke hardware tick uit op de CPU
#                 self.cpu.tick()
                
#                 # # ENKELE TICK VOOR DE IO CONTROLLER (Achtergrond-renderers van displays verversen)
#                 # self.io_controller.tick()
#                 # 2. I/O Controller tikt op een lagere frequentie
#                 if self.totale_ticks % IO_PRESCALER == 0:
#                     self.io_controller.tick()
                
#                 self.totale_ticks += 1

#                 if self.show_log:
#                     # --- VANG STATUS OP VAN MASTER EN CONTEXTEN VOOR DE TICK ---
#                     master_state = self.cpu.fsm_state
#                     master_pc = self.cpu.PC
#                     master_mir = getattr(self.cpu, 'MIR', 'None')
#                     if master_mir is None: master_mir = 'None'
                
#                     # Verzamel de status van de actieve hardware-threads (contexts)
#                     context_logs = []
#                     for idx, ctx in enumerate(self.cpu.contexts):
#                         ctx_state = getattr(ctx, 'fsm_state', '???')
#                         ctx_pc = getattr(ctx, 'PC', '?')
#                         ctx_mir = getattr(ctx, 'MIR', 'None')
#                         if ctx_mir is None: ctx_mir = 'None'
                        
#                         context_logs.append(
#                             f"   [Thread {idx}] State: {ctx_state:<7} | PC: {ctx_pc:<2} | MIR: {ctx_mir:<12}"
#                         )
                    
#                     # --- PRINT ALLES NETJES ONDER ELKAAR ---
#                     master_log = f"Tick {self.totale_ticks:02d} | MASTER -> State: {master_state:<7} | PC: {master_pc:<2} | MIR: {master_mir:<12}"
#                     print(master_log)
#                     for c_log in context_logs:
#                         print(c_log)
                    
#             else:
#                 self.io_controller.tick()       # flush the IO pipeline
#                 break
                
#         # 2. BINNEN-FRAME REFRESH: Update de uCore LEDs op het frontpaneel
#         self.panel.update_cores(self.cpu.cores)
        
#         # Dwing Tkinter om de LEDs en aangesloten IO-peripherals direct te hertekenen
#         self.root.update_idletasks() 

#         # 3. STOP CONDITIE: Als de CPU op HALT staat en alle cores idle zijn, stoppen we de klok
#         if self.cpu.is_completely_idle():
#             eind_tijd = time.perf_counter()
#             totale_tijd = eind_tijd - self.start_tijd
#             khz = (self.totale_ticks / totale_tijd) / 1000
            
#             # Roep de uitgebreide eindrapportage aan
#             self.print_eindrapportage(totale_tijd, khz)
#             return  # Stop de gameloop definitief

#         # 4. Naar de volgende kloktik!
#         self.root.after(0, self.gameloop)

#     def print_eindrapportage(self, totale_tijd, khz):
#         """Drukt de complete eindstatus en geheugendump af."""
#         print("\n==========================================================")
#         print("             SIMULATIE SUCCESVOL BEËINDIGD                ")
#         print("==========================================================")
#         print(f"Totale Ticks: {self.totale_ticks}")
#         print(f"Totale Tijd:  {totale_tijd:.4f} seconden")
#         print(f"Snelheid:     {khz:.2f} kHz op de host machine.")
#         print("==========================================================\n")

#         # --- GEAVANCEERD MATRIX STATUS RAPPORT ---
#         print("\033[92m\n==========================================================")
#         print("                EINDSTATUS STERN MATRIX                   ")
#         print("==========================================================")
#         print(f"Vrije Cores over in wachtrij ({len(self.cpu.free_cores)}/32):\n {list(self.cpu.free_cores)}")
#         print("----------------------------------------------------------")
#         print(f"{'Core':<6} | {'Status':<8} | {'Waarde':<8} | {'Gekoppeld Register':<20}")
#         print("----------------------------------------------------------")
        
#         reg_names = {0: "I (R0)", 1: "A (R1)", 2: "B (R2)", 3: "C (R3)", 4: "K (R4)", 
#                     5: "L (R5)", 6: "M (R6)", 7: "X (R7)", 8: "Y (R8)", 9: "Z (R9)"}
        
#         core_to_reg = {}
#         for reg_id, core_id in self.cpu.registers.items():
#             if core_id is not None:
#                 naam = reg_names.get(reg_id, f"R{reg_id}")
#                 core_to_reg[core_id] = f"Register {naam}"
                
#         if self.cpu.last_test_core is not None:
#             if self.cpu.last_test_core in core_to_reg:
#                 core_to_reg[self.cpu.last_test_core] += " + Status (last_test)"
#             else:
#                 core_to_reg[self.cpu.last_test_core] = "Status (last_test)"
                
#         for c_id, core in enumerate(self.cpu.cores):
#             status = core.coreStatus
#             val = core.value
#             reg_naam = core_to_reg.get(c_id, "-")
            
#             if reg_naam != "-":
#                 print(f"Core {c_id:<2} | {status:<8} | {val:>10} | <-- {reg_naam}")
#             else:
#                 print(f"Core {c_id:<2} | {status:<8} | {val:>10} | {reg_naam}")
                
#         print("==========================================================\n")

#         # --- GEHEUGEN DUMP (Vanaf 512 voor de cryptografie) ---
#         print("==========================================================")
#         print("             GEHEUGEN DUMP (Adres 1023 - 23)              ")
#         print("==========================================================")
        
#         start_adres = 1024 - 10
#         aantal_adressen = 10
        
#         for i in range(aantal_adressen):
#             current_addr = start_adres + i
#             if current_addr < self.cpu.memory.memSize():
#                 waarde = self.cpu.memory.memRead(current_addr)
                
#                 if 32 <= waarde <= 126:
#                     char_repr = f"'{chr(waarde)}'"
#                 else:
#                     char_repr = "???"
                    
#                 label = " <-- Master Key (M)" if current_addr == 512 else ""
#                 print(f"Adres {current_addr:<3} | Waarde: {waarde:>10} | Karakter: {char_repr:<5}{label}")
                
#         print("==========================================================\033[0m\n")


# # --- DIRECTE UITVOERING ---
# if __name__ == "__main__":
#     mainboard = SternZ32Mainboard()
#     mainboard.start()

# import os
# import sys
# import time
# import tkinter as tk
# from assemblerV2 import assemble
# from frontpanelZ32G import FrontPanel
# from InmosZ32A import CPU
# from IOcontroller import IOController
# from memoryMMU import MMU  # 1. Importeer de nieuwe MMU!
# from opcodes import context_stress, display_test, encrypt_program


# class SternZ32Mainboard:

#     def __init__(self):
#         print("--- INITIALISEER STERN-Z32 PLATFORM (1 CPU + MMU) ---")

#         # 1. Start de Master GUI Root
#         self.root = tk.Tk()
#         self.root.title("STERN-Z32 Mainboard Central Clock (Single CPU + MMU)")
#         self.root.configure(bg="#1e1e1e")

#         # 2. Initialiseer de Centrale MMU op het mainboard
#         self.mmu = MMU(Page0=1024, Private=512, Shared=1024, block_size=64)

#         # 3. Initialiseer CPU 0 en koppel de centrale MMU via Dependency Injection
#         self.cpu = CPU(cpu_id=0, memory=self.mmu)
#         self.show_log = False

#         # 4. Soldeer de IOController op het mainboard chipset-vlak
#         self.io_controller = IOController(self.root)
#         self.cpu.IO(self.io_controller)

#         # 5. Koppel het Frontpanel
#         self.panel = FrontPanel(self.root, num_cores=32)

#         # 6. Firmware laden
#         test_program = []
#         if len(sys.argv) > 1:
#             firmware_pad = sys.argv[1]
#             if os.path.exists(firmware_pad):
#                 print(f"Firmware gevonden! Laden van: {firmware_pad}")
#                 try:
#                     with open(firmware_pad, "r") as f:
#                         test_program = [
#                             int(line.strip()) for line in f if line.strip()
#                         ]
#                     print(
#                         f"Firmware succesvol geladen ({len(test_program)}"
#                         " instructies)."
#                     )
#                 except ValueError as e:
#                     print(
#                         f"Fout tijdens parsen van {firmware_pad}: {e}",
#                         file=sys.stderr,
#                     )
#                     sys.exit(1)
#             else:
#                 print(
#                     f"Fout: Opgegeven firmwarebestand '{firmware_pad}' niet"
#                     " gevonden!",
#                     file=sys.stderr,
#                 )
#                 sys.exit(1)
#         else:
#             print(
#                 "Geen externe firmware opgegeven. Fallback naar"
#                 " 'encrypt_program'..."
#             )
#             test_program = assemble(encrypt_program)

#         print(f"Gegenereerde/Geladen machinecode: {test_program}\n")

#         # Schrijf de machinecode rechtstreeks in de ROM (progMem) van de MMU
#         self.mmu.write_rom(test_program, start_adres=0)

#         # Systeemtellers & Performance Tuning
#         self.totale_ticks = 0
#         self.cycles_per_frame = 50

#     def start(self):
#         """Start de master clock van de emulator en geeft de controle over aan Tkinter"""
#         print("--- START CPU MATRIX + IO SIMULATIE ---")
#         self.start_tijd = time.perf_counter()
#         self.gameloop()
#         self.root.mainloop()

#     def gameloop(self):
#         """De ononderbroken klok-trein van de Inmos-Z32, MMU en IO-Controller"""
#         IO_PRESCALER = 5000

#         for _ in range(self.cycles_per_frame):
#             if not self.cpu.is_completely_idle():
#                 # A. Voer de hardware tick uit op CPU 0
#                 self.cpu.tick()

#                 # B. CRUCIAAL: Sluit de klokcyclus af op de MMU (vrijgeven van bus-locks)
#                 self.mmu.tick()

#                 # C. I/O Controller tikt op een lagere frequentie
#                 if self.totale_ticks % IO_PRESCALER == 0:
#                     self.io_controller.tick()

#                 self.totale_ticks += 1

#                 if self.show_log:
#                     master_state = self.cpu.fsm_state
#                     master_pc = self.cpu.PC
#                     master_mir = getattr(self.cpu, "MIR", "None") or "None"

#                     context_logs = []
#                     for idx, ctx in enumerate(self.cpu.contexts):
#                         ctx_state = getattr(ctx, "fsm_state", "???")
#                         ctx_pc = getattr(ctx, "PC", "?")
#                         ctx_mir = getattr(ctx, "MIR", "None") or "None"
#                         context_logs.append(
#                             f"   [Thread {idx}] State: {ctx_state:<7} | PC:"
#                             f" {ctx_pc:<2} | MIR: {ctx_mir:<12}"
#                         )

#                     master_log = (
#                         f"Tick {self.totale_ticks:02d} | MASTER -> State:"
#                         f" {master_state:<7} | PC: {master_pc:<2} | MIR:"
#                         f" {master_mir:<12}"
#                     )
#                     print(master_log)
#                     for c_log in context_logs:
#                         print(c_log)

#             else:
#                 self.io_controller.tick()  # Flush the IO pipeline
#                 break

#         # BINNEN-FRAME REFRESH
#         self.panel.update_cores(self.cpu.cores)
#         self.root.update_idletasks()

#         # STOP CONDITIE
#         if self.cpu.is_completely_idle():
#             eind_tijd = time.perf_counter()
#             totale_tijd = eind_tijd - self.start_tijd
#             khz = (self.totale_ticks / totale_tijd) / 1000

#             self.print_eindrapportage(totale_tijd, khz)
#             return

#         self.root.after(0, self.gameloop)

#     def print_eindrapportage(self, totale_tijd, khz):
#         """Drukt de complete eindstatus en geheugendump af."""
#         print("\n==========================================================")
#         print("             SIMULATIE SUCCESVOL BEËINDIGD                ")
#         print("==========================================================")
#         print(f"Totale Ticks: {self.totale_ticks}")
#         print(f"Totale Tijd:  {totale_tijd:.4f} seconden")
#         print(f"Snelheid:     {khz:.2f} kHz op de host machine.")
#         print("==========================================================\n")

#         # Matrix status rapport
#         print(
#             "\033[92m\n=========================================================="
#         )
#         print("                EINDSTATUS STERN MATRIX                   ")
#         print("==========================================================")
#         print(
#             f"Vrije Cores over in wachtrij ({len(self.cpu.free_cores)}/32):\n"
#             f" {list(self.cpu.free_cores)}"
#         )
#         print("----------------------------------------------------------")
#         print(
#             f"{'Core':<6} | {'Status':<8} | {'Waarde':<8} | {'Gekoppeld'  ' Register':<20}"
#         )
#         print("----------------------------------------------------------")

#         reg_names = {
#             0: "I (R0)",
#             1: "A (R1)",
#             2: "B (R2)",
#             3: "C (R3)",
#             4: "K (R4)",
#             5: "L (R5)",
#             6: "M (R6)",
#             7: "X (R7)",
#             8: "Y (R8)",
#             9: "Z (R9)",
#         }

#         core_to_reg = {}
#         for reg_id, core_id in self.cpu.registers.items():
#             if core_id is not None:
#                 naam = reg_names.get(reg_id, f"R{reg_id}")
#                 core_to_reg[core_id] = f"Register {naam}"

#         if self.cpu.last_test_core is not None:
#             if self.cpu.last_test_core in core_to_reg:
#                 core_to_reg[self.cpu.last_test_core] += " + Status (last_test)"
#             else:
#                 core_to_reg[self.cpu.last_test_core] = "Status (last_test)"

#         for c_id, core in enumerate(self.cpu.cores):
#             status = core.coreStatus
#             val = core.value
#             reg_naam = core_to_reg.get(c_id, "-")

#             if reg_naam != "-":
#                 print(
#                     f"Core {c_id:<2} | {status:<8} | {val:>10} | <-- {reg_naam}"
#                 )
#             else:
#                 print(f"Core {c_id:<2} | {status:<8} | {val:>10} | {reg_naam}")

#         print("==========================================================\n")

#         # Geheugen Dump via MMU (Shared / Private geheugen)
#         print("==========================================================")
#         print("             GEHEUGEN DUMP (Adres 1024 t/m 1033)          ")
#         print("==========================================================")

#         start_adres = 1024
#         aantal_adressen = 10

#         for i in range(aantal_adressen):
#             current_addr = start_adres + i
#             if current_addr < self.mmu.memSize():
#                 waarde = self.mmu.memRead(current_addr, cpu_id=0)

#                 if 32 <= waarde <= 126:
#                     char_repr = f"'{chr(waarde)}'"
#                 else:
#                     char_repr = "???"

#                 print(
#                     f"Adres {current_addr:<4} | Waarde: {waarde:>10} |"
#                     f" Karakter: {char_repr:<5}"
#                 )

#         print("==========================================================\033[0m\n")


# if __name__ == "__main__":
#     mainboard = SternZ32Mainboard()
#     mainboard.start()


import os
import sys
import time
import tkinter as tk
from assemblerV2 import assemble
from frontpanelZ32G import FrontPanel
from InmosZ32A import CPU
from IOcontroller import IOController
from memoryMMU import MMU
from opcodes import context_stress, display_test, encrypt_program


class SternZ32Mainboard:

    def __init__(self, num_cpus=1):
        self.num_cpus = num_cpus
        print(
            f"--- INITIALISEER STERN-Z32 PLATFORM ({self.num_cpus} CPU(s) +"
            " MMU) ---"
        )

        # 1. Start de Master GUI Root
        self.root = tk.Tk()
        self.root.title(
            f"STERN-Z32 Mainboard Central Clock - [{self.num_cpus} CPU(s)]"
        )
        self.root.configure(bg="#1e1e1e")

        # 2. Initialiseer de Centrale MMU (Andrew S. geheugenbus)
        self.mmu = MMU(Page0=1024, Private=512, Shared=1024, block_size=64)

        # 3. Dynamische CPU Matrix aanmaken
        self.cpus = [
            CPU(cpu_id=i, memory=self.mmu) for i in range(self.num_cpus)
        ]
        self.show_log = True

        # 4. Soldeer de IOController op het mainboard en koppel aan Master CPU 0
        self.io_controller = IOController(self.root)
        self.cpus[0].IO(self.io_controller)

        # 5. Koppel het Frontpanel (toont Edsgar-cores van Master CPU 0)
        self.panel = FrontPanel(self.root, num_cores=32)

        # 6. Firmware laden
        test_program = []
        firmware_pad = None

        if len(sys.argv) > 1:
            firmware_pad = sys.argv[1]

        if firmware_pad and os.path.exists(firmware_pad):
            print(f"Firmware gevonden! Laden van: {firmware_pad}")
            try:
                with open(firmware_pad, "r") as f:
                    test_program = [
                        int(line.strip()) for line in f if line.strip()
                    ]
                print(
                    f"Firmware succesvol geladen ({len(test_program)}"
                    " instructies)."
                )
            except ValueError as e:
                print(
                    f"Fout tijdens parsen van {firmware_pad}: {e}",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                "Geen (geldige) externe firmware opgegeven. Fallback naar"
                " 'encrypt_program'..."
            )
            test_program = assemble(encrypt_program)

        print(f"Gegenereerde/Geladen machinecode: {test_program}\n")

        # Schrijf de machinecode in de ROM van de centrale MMU
        self.mmu.write_rom(test_program, start_adres=0)

        # Systeemtellers & Performance Tuning
        self.totale_ticks = 0
        self.cycles_per_frame = 50

    def is_system_idle(self):
        """Controleert of alle aangesloten CPU's idle/HALT zijn."""
        return all(cpu.is_completely_idle() for cpu in self.cpus)

    def start(self):
        """Start de master clock van de emulator"""
        print(f"--- START SYSTEM SIMULATIE MET {self.num_cpus} CPU(S) ---")
        self.start_tijd = time.perf_counter()
        self.gameloop()
        self.root.mainloop()

    def gameloop(self):
        """De centrale klok-pulse die alle CPU's en de MMU synchroon tikt."""
        IO_PRESCALER = 5000

        for _ in range(self.cycles_per_frame):
            if not self.is_system_idle():
                # A. Tik elke actieve CPU binnen exact dezelfde klokcyclus
                for cpu in self.cpus:
                    if not cpu.is_completely_idle():
                        cpu.tick()

                # B. Sluit de klokcyclus af op de MMU (wissen van bus-locks)
                self.mmu.tick()

                # C. I/O Controller verversen
                if self.totale_ticks % IO_PRESCALER == 0:
                    self.io_controller.tick()

                self.totale_ticks += 1

                # D. Optionele logging
                if self.show_log:
                    log_items = [f"Tick {self.totale_ticks:02d}"]
                    for cpu in self.cpus:
                        log_items.append(
                            f"CPU{cpu.ID}: {cpu.fsm_state:<7} (PC: {cpu.PC:<2})"
                        )
                    print(" | ".join(log_items))

            else:
                self.io_controller.tick()
                break

        # Interface verversen (toont cores van CPU 0)
        self.panel.update_cores(self.cpus[0].cores)
        self.root.update_idletasks()

        # Stop-conditie wanneer ALLE CPU's idle zijn
        if self.is_system_idle():
            eind_tijd = time.perf_counter()
            totale_tijd = eind_tijd - self.start_tijd
            khz = (self.totale_ticks / totale_tijd) / 1000
            self.print_eindrapportage(totale_tijd, khz)
            return

        self.root.after(0, self.gameloop)

    def print_eindrapportage(self, totale_tijd, khz):
        """Drukt de eindrapportage af van het gehele systeem."""
        print("\n==========================================================")
        print("             SIMULATIE SUCCESVOL BEËINDIGD                ")
        print("==========================================================")
        print(f"Aantal CPU's: {self.num_cpus}")
        print(f"Totale Ticks: {self.totale_ticks}")
        print(f"Totale Tijd:  {totale_tijd:.4f} seconden")
        print(f"Snelheid:     {khz:.2f} kHz op de host machine.")
        print("==========================================================\n")

        for cpu in self.cpus:
            print(
                f"\033[92m--- EINDSTATUS CPU {cpu.ID} (Vrije Cores:"
                f" {len(cpu.free_cores)}/32) ---"
            )
            print(f"  FSM State: {cpu.fsm_state} | PC: {cpu.PC}\033[0m")

        print("\n==========================================================")
        print("          SHARED GEHEUGEN DUMP (Adres 1024 t/m 1033)      ")
        print("==========================================================")
        for addr in range(1024, 1034):
            waarde = self.mmu.memRead(addr, cpu_id=0)
            print(f"Adres {addr:<4} | Waarde: {waarde:>10}")
        print("==========================================================\n")


# --- DIRECTE UITVOERING ---
if __name__ == "__main__":
    # Lees optioneel het aantal CPU's als 2e command-line argument
    # Gebruik: python SternZ32A.py [firmware.bin] [aantal_cpus]
    aantal_cpus = 1

    if len(sys.argv) > 2:
        try:
            aantal_cpus = int(sys.argv[2])
        except ValueError:
            print(
                f"Ongeldig aantal CPU's '{sys.argv[2]}', terugval naar 1 CPU."
            )

    mainboard = SternZ32Mainboard(num_cpus=aantal_cpus)
    mainboard.start()