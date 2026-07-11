# SternZ32G.py
import tkinter as tk
import time
from InmosZ32G import CPU
from opcodes import context_stress, display_test
from assembler import assemble
from frontpanelZ32G import FrontPanel
from IOcontroller import IOController  # Importeer de nieuwe IO-chip!


class SternZ32Mainboard:
    def __init__(self):
        print("--- INITIALISEER STERN-Z32 PLATFORM (EVENT-DRIVEN) ---")
        
        # 1. Start de Master GUI Root die het ritme en de venster-contexts bepaalt
        self.root = tk.Tk()
        self.root.title("STERN-Z32 Mainboard Central Clock")
        self.root.configure(bg="#1e1e1e")
        
        # 2. Initialiseer de CPU hardware matrix (32 cores + context switches)
        self.cpu = CPU()
        self.show_log = True
        
        # 3. UPGRADE: Soldeer de IOController op het mainboard chipset-vlak
        # We geven de master root mee zodat de schermen en toetsenbord-bindings direct werken
        self.io_controller = IOController(self.root)

        # Koppel het toetsenbord
        self.root.bind("<Key>", self.io_controller.hardware_keyboard_callback)
        
        # Koppel de IO-controller ook direct aan de CPU, zodat OUT/IN/IOSYNC hardware-instructies
        # direct via de interne bus met self.io_controller kunnen praten.
        self.cpu.IO(self.io_controller)           # Solder jumper when the right CPU is installed
        
        # 4. Koppel en bed (embed) het Frontpanel in deze root
        self.panel = FrontPanel(self.root, num_cores=32)
        
        # 5. Vertaal het testprogramma via de assembler en laad het in het geheugen
        test_program = assemble(display_test)  
        print(f"Gegenereerde machinecode: {test_program}\n")
        
        for adres, machine_woord in enumerate(test_program):
            self.cpu.memory.memWrite(machine_woord, adres)
            
        # Systeemtellers & Performance Tuning
        self.totale_ticks = 0
        self.cycles_per_frame = 50  # Aantal CPU-ticks dat we per GUI-yield wegtikken

    def start(self):
        """Start de master clock van de emulator en geeft de controle over aan Tkinter"""
        print("--- START CPU MATRIX + IO SIMULATIE ---")
        self.start_tijd = time.perf_counter()
        self.gameloop()
        self.root.mainloop()  # De hoofd event-loop van Tkinter draait nu het systeem

    def gameloop(self):
        """De ononderbroken klok-trein (Heartbeat) van de Inmos-Z32 en IO-Controller"""
    
        # 1. Bestook de CPU en chipset met een batch kloktikken
        for _ in range(self.cycles_per_frame):
            if not self.cpu.is_completely_idle():
                # Voer de werkelijke hardware tick uit op de CPU
                self.cpu.tick()
                
                # ENKELE TICK VOOR DE IO CONTROLLER (Achtergrond-renderers van displays verversen)
                self.io_controller.tick()
                
                self.totale_ticks += 1

                if self.show_log:
                    # --- VANG STATUS OP VAN MASTER EN CONTEXTEN VOOR DE TICK ---
                    master_state = self.cpu.fsm_state
                    master_pc = self.cpu.PC
                    master_mir = getattr(self.cpu, 'MIR', 'None')
                    if master_mir is None: master_mir = 'None'
                
                    # Verzamel de status van de actieve hardware-threads (contexts)
                    context_logs = []
                    for idx, ctx in enumerate(self.cpu.contexts):
                        ctx_state = getattr(ctx, 'fsm_state', '???')
                        ctx_pc = getattr(ctx, 'PC', '?')
                        ctx_mir = getattr(ctx, 'MIR', 'None')
                        if ctx_mir is None: ctx_mir = 'None'
                        
                        context_logs.append(
                            f"   [Thread {idx}] State: {ctx_state:<7} | PC: {ctx_pc:<2} | MIR: {ctx_mir:<12}"
                        )
                    
                    # --- PRINT ALLES NETJES ONDER ELKAAR ---
                    master_log = f"Tick {self.totale_ticks:02d} | MASTER -> State: {master_state:<7} | PC: {master_pc:<2} | MIR: {master_mir:<12}"
                    print(master_log)
                    for c_log in context_logs:
                        print(c_log)
                    
            else:
                break
                
        # 2. BINNEN-FRAME REFRESH: Update de uCore LEDs op het frontpaneel
        self.panel.update_cores(self.cpu.cores)
        
        # Dwing Tkinter om de LEDs en aangesloten IO-peripherals direct te hertekenen
        self.root.update_idletasks() 

        # 3. STOP CONDITIE: Als de CPU op HALT staat en alle cores idle zijn, stoppen we de klok
        if self.cpu.is_completely_idle():
            eind_tijd = time.perf_counter()
            totale_tijd = eind_tijd - self.start_tijd
            khz = (self.totale_ticks / totale_tijd) / 1000
            
            # Roep de uitgebreide eindrapportage aan
            self.print_eindrapportage(totale_tijd, khz)
            return  # Stop de gameloop definitief

        # 4. Naar de volgende kloktik!
        self.root.after(0, self.gameloop)

    def print_eindrapportage(self, totale_tijd, khz):
        """Drukt de complete eindstatus en geheugendump af."""
        print("\n==========================================================")
        print("             SIMULATIE SUCCESVOL BEËINDIGD                ")
        print("==========================================================")
        print(f"Totale Ticks: {self.totale_ticks}")
        print(f"Totale Tijd:  {totale_tijd:.4f} seconden")
        print(f"Snelheid:     {khz:.2f} kHz op de host machine.")
        print("==========================================================\n")

        # --- GEAVANCEERD MATRIX STATUS RAPPORT ---
        print("\033[92m\n==========================================================")
        print("                EINDSTATUS STERN MATRIX                   ")
        print("==========================================================")
        print(f"Vrije Cores over in wachtrij ({len(self.cpu.free_cores)}/32):\n {list(self.cpu.free_cores)}")
        print("----------------------------------------------------------")
        print(f"{'Core':<6} | {'Status':<8} | {'Waarde':<8} | {'Gekoppeld Register':<20}")
        print("----------------------------------------------------------")
        
        reg_names = {0: "I (R0)", 1: "A (R1)", 2: "B (R2)", 3: "C (R3)", 4: "K (R4)", 
                    5: "L (R5)", 6: "M (R6)", 7: "X (R7)", 8: "Y (R8)", 9: "Z (R9)"}
        
        core_to_reg = {}
        for reg_id, core_id in self.cpu.registers.items():
            if core_id is not None:
                naam = reg_names.get(reg_id, f"R{reg_id}")
                core_to_reg[core_id] = f"Register {naam}"
                
        if self.cpu.last_test_core is not None:
            if self.cpu.last_test_core in core_to_reg:
                core_to_reg[self.cpu.last_test_core] += " + Status (last_test)"
            else:
                core_to_reg[self.cpu.last_test_core] = "Status (last_test)"
                
        for c_id, core in enumerate(self.cpu.cores):
            status = core.coreStatus
            val = core.value
            reg_naam = core_to_reg.get(c_id, "-")
            
            if reg_naam != "-":
                print(f"Core {c_id:<2} | {status:<8} | {val:>10} | <-- {reg_naam}")
            else:
                print(f"Core {c_id:<2} | {status:<8} | {val:>10} | {reg_naam}")
                
        print("==========================================================\n")

        # --- GEHEUGEN DUMP (Vanaf 512 voor de cryptografie) ---
        print("==========================================================")
        print("             GEHEUGEN DUMP (Adres 512 t/m 562)            ")
        print("==========================================================")
        
        start_adres = 512
        aantal_adressen = 10
        
        for i in range(aantal_adressen):
            current_addr = start_adres + i
            if current_addr < self.cpu.memory.memSize():
                waarde = self.cpu.memory.memRead(current_addr)
                
                if 32 <= waarde <= 126:
                    char_repr = f"'{chr(waarde)}'"
                else:
                    char_repr = "???"
                    
                label = " <-- Master Key (M)" if current_addr == 512 else ""
                print(f"Adres {current_addr:<3} | Waarde: {waarde:>10} | Karakter: {char_repr:<5}{label}")
                
        print("==========================================================\033[0m\n")


# --- DIRECTE UITVOERING ---
if __name__ == "__main__":
    mainboard = SternZ32Mainboard()
    mainboard.start()