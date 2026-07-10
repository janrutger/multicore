# SternZ32.py
import tkinter as tk
import time
from InmosZ32 import CPU
from opcodes import context_stress
from assembler import assemble
from frontpanelZ32G import FrontPanel

# class FrontPanel:
#     def __init__(self, master_root, num_cores=32):
#         """
#         Geïntegreerd Frontpaneel dat meelift op de gedeelde root van het mainboard.
#         Dit voorkomt Tkinter-overhead en multi-loop crashes.
#         """
#         self.root = master_root
        
#         # Optioneel: Je kunt de titel van de root hier overschrijven of aanpassen
#         self.root.title("STERN-Z32 Central Dashboard & Frontpanel")
        
#         self.leds = []
        
#         # Dynamische grid-indeling (bijv. 8 kolommen breed voor 32 cores)
#         kolommen = 8
        
#         # Bouw de LED-matrix op binnen de meegegeven root
#         for i in range(num_cores):
#             row = i // kolommen
#             col = i % kolommen
            
#             # Frame voor de layout van deze specifieke core LED
#             frame = tk.Frame(self.root, bg="#1e1e1e", padx=10, pady=10)
#             frame.grid(row=row, column=col)
            
#             # De LED zelf (een Canvas cirkel)
#             canvas = tk.Canvas(frame, width=30, height=30, bg="#1e1e1e", highlightthickness=0)
#             canvas.pack()
            
#             # Teken de initiële rode (IDLE) cirkel
#             circle = canvas.create_oval(2, 2, 28, 28, fill="#ff0000", outline="#3a3a3a")
            
#             # Label voor het Core ID
#             label = tk.Label(frame, text=f"Core {i:02d}", fg="#888888", bg="#1e1e1e", font=("Courier", 8))
#             label.pack()
            
#             self.leds.append((canvas, circle))
            
#     def update_cores(self, cores):
#         """Update de kleuren van de LEDs live op basis van de werkelijke uCore statussen."""
#         color_map = {
#             'IDLE': '#ff0000',     # Fel rood
#             'WORKING': '#ffaa00',  # Oranje/Geel
#             'VALID': '#00ff00'     # Groen (Data staat klaar!)
#         }
        
#         for i, core in enumerate(cores):
#             # Veiligheidsklepje voor het geval de CPU minder cores heeft dan het paneel
#             if i >= len(self.leds):
#                 break
                
#             canvas, circle = self.leds[i]
#             color = color_map.get(core.coreStatus, '#555555')
#             canvas.itemconfig(circle, fill=color)



class SternZ32Mainboard:
    def __init__(self):
        print("--- INITIALISEER STERN-Z32 PLATFORM (EVENT-DRIVEN) ---")
        
        # 1. Start de Master GUI Root die het ritme bepaalt
        self.root = tk.Tk()
        self.root.title("STERN-Z32 Mainboard Central Clock")
        self.root.configure(bg="#1e1e1e")
        
        # 2. Initialiseer de CPU hardware matrix
        self.cpu = CPU()
        self.show_log = False
        
        # 3. Koppel en bed (embed) het Frontpanel in deze root
        self.panel = FrontPanel(self.root, num_cores=32)
        
        # 4. Vertaal het testprogramma via de assembler en laad het in het geheugen
        test_program = assemble(context_stress)  
        print(f"Gegenereerde machinecode: {test_program}\n")
        
        for adres, machine_woord in enumerate(test_program):
            self.cpu.memory.memWrite(machine_woord, adres)
            
        # Systeemtellers & Performance Tuning
        self.totale_ticks = 0
        self.cycles_per_frame = 1  # Aantal CPU-ticks dat we per GUI-yield wegtikken
        self.start_tijd = time.perf_counter()

    def start(self):
        """Start de master clock van de emulator en geeft de controle over aan Tkinter"""
        print("--- START CPU MATRIX SIMULATIE ---")
        self.gameloop()
        self.root.mainloop()  # De hoofd event-loop van Tkinter draait nu het systeem




    def gameloop(self):
        """De ononderbroken klok-trein (Heartbeat) van de Inmos-Z32"""
    
        # 1. Bestook de CPU met een batch kloktikken (in jouw geval 1)
        for _ in range(self.cycles_per_frame):
            if not self.cpu.is_completely_idle():
                 # Voer de werkelijke hardware tick uit
                self.cpu.tick()
                # self.io_controller.tick(self.cpu)
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
        
        # Dwing Tkinter om de LEDs direct te hertekenen
        self.root.update_idletasks() 

        # 3. STOP CONDITIE: Als de CPU op HALT staat en alle cores idle zijn, stoppen we de klok
        if self.cpu.is_completely_idle():
            eind_tijd = time.perf_counter()
            totale_tijd = eind_tijd - self.start_tijd
            khz = (self.totale_ticks / totale_tijd) / 1000
            
            # Roep de uitgebreide eindrapportage aan
            self.print_eindrapportage(totale_tijd, khz)
            return  # Stop de gameloop definitief

        # 4. Naar de volgende tick!
        self.root.after(0, self.gameloop)

    def print_eindrapportage(self, totale_tijd, khz):
        """Drukt de complete eindstatus en geheugendump af voor krachtig debuggen."""
        print("\n==========================================================")
        print("             SIMULATIE SUCCESVOL BEËINDIGD                ")
        print("==========================================================")
        print(f"Totale Ticks: {self.totale_ticks}")
        print(f"Totale Tijd:  {totale_tijd:.4f} seconden")
        print(f"Snelheid:     {khz:.2f} kHz op de host machine.")
        print("==========================================================\n")

        # --- MASTER CPU REGISTERS EINDSTATUS ---
        print("==========================================================")
        print("             MASTER CPU REGISTERS EINDSTATUS              ")
        print("==========================================================")
        if hasattr(self.cpu, 'registers'):
            # Netjes sorteren op register-index/naam indien mogelijk
            for reg_name, reg_val in sorted(self.cpu.registers.items()):
                # Map eventueel index terug naar letters voor de leesbaarheid
                reg_labels = {0:'I', 1:'A', 2:'B', 3:'C', 4:'K', 5:'L', 6:'M', 7:'X', 8:'Y', 9:'Z'}
                label = reg_labels.get(reg_name, f"R{reg_name}")
                print(f"Register {label:<2} : {reg_val}")
        print(f"Program Counter (PC) : {self.cpu.PC}")
        print(f"Stack Pointer (SP)   : {self.cpu.SP}")
        print("==========================================================\n")

        # --- GEHEUGEN DUMP (Vaf 512 voor de cryptografie) ---
        print("==========================================================")
        print("             GEHEUGEN DUMP (Adres 512 t/m 562)            ")
        print("==========================================================")
        
        start_adres = 512
        aantal_adressen = 50
        
        for i in range(aantal_adressen):
            current_addr = start_adres + i
            if current_addr < self.cpu.memory.memSize():
                waarde = self.cpu.memory.memRead(current_addr)
                
                # Vertaal naar karakter als het binnen de leesbare ASCII-reeks valt
                if 32 <= waarde <= 126:
                    char_repr = f"'{chr(waarde)}'"
                else:
                    char_repr = "???"
                    
                label = " <-- Master Key (M)" if current_addr == 512 else ""
                print(f"Adres {current_addr:<3} | Waarde: {waarde:>10} | Karakter: {char_repr:<5}{label}")
                
        print("==========================================================\n")

        

# --- DIRECTE UITVOERING ---
if __name__ == "__main__":
    mainboard = SternZ32Mainboard()
    mainboard.start()

    