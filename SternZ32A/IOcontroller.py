import tkinter as tk
import sys

from tekstdisplay  import textDisplay 
from graphDisplay  import GraphicalDisplay

class IOController:
    def __init__(self, master_root):
        """
        De hardware IO-Controller chip voor het SternZ32 platform.
        Beheert de registers reg0 t/m reg6 en wikkelt communicatie asynchroon af.
        """
        self.root = master_root
        
        # 1. Interne Hardware Registers van de IO-Controller
        self.registers = {
            0: 0,  # reg0: Device Type (1 = Karakter, 2 = Grafisch)
            1: 0,  # reg1: Value 1 (Char of Kleur)
            2: 0,  # reg2: Value 2 (X-coördinaat)
            3: 0,  # reg3: Value 3 (Y-coördinaat)
            4: 0,  # reg4: Value 4 (Gereserveerd)
            5: 0,  # reg5: Instruction / Trigger (1=print, 2=plot, 3=clear, 4=setcursor)
            6: 0   # reg6: KBD Input Data (ASCII waarde)
        }
        
        # 2. Hardware Status Flags
        self.write_flag = 0
        self.read_flag = 0
        
        # 3. Hardware Buffers
        self.kbd_buffer = []
        
        # 4. Koppeling met de fysieke Peripherals (zet de boel aan)
        
        self.text_device      = textDisplay(master_root=self.root)
        self.graphical_device = GraphicalDisplay(master_root=self.root)
        
        # Initialiseer Toetsenbord-hardware binding op het hoofdvenster
        self.root.bind("<Key>", self.hardware_keyboard_callback)
        

    def hardware_keyboard_callback(self, event):
        """Achtergrond-tick interceptor: Vangt fysieke sleutels op en buffert ze."""
        if event.char:
            char_code = ord(event.char)
            self.kbd_buffer.append(char_code)


    # --- CPU BUS INTERFACE INSTRUCTIES ---

    def cpu_out(self, reg_num, value):
        """
        Uitvoering van de OUT Rx reg# instructie.
        Returnt True als de schrijfactie slaagt, of False als de core moet STALLEN.
        """
        if self.write_flag == 1:
            return False  # IO-Controller is bezet -> STALL de CPU core!
        
        if reg_num in self.registers:
            self.registers[reg_num] = value
            # Het schrijven naar reg5 triggert direct de hardware write-flag!
            if reg_num == 5:
                self.write_flag = 1
                
        return True

    def cpu_in(self, reg_num):
        """
        Uitvoering van de IN Rx reg# instructie.
        Leest het register (meestal reg6) en reset de read-flag conform specificatie.
        """
        val = self.registers.get(reg_num, 0)
        if reg_num == 6:
            self.read_flag = 0  # CPU heeft data verwerkt, zet flag op 0
        return val

    def cpu_iosync(self):
        """
        Uitvoering van de IOSYNC instructie (Non-blocking tick).
        Verwerkt zowel de write-sectie als de read-sectie van de controller.
        """
        # --- WRITE SECTIE ---
        if self.write_flag == 1:
            dev_type = self.registers[0]
            inst_code = self.registers[5]
            
            # Vertaal hardware instructie-id naar string commando's voor devices
            cmd_map = {1: "print", 2: "plot", 3: "clear", 4: "move_cursor"}
            inst_str = cmd_map.get(inst_code, "unknown")
            
            if dev_type == 1:  # Character Display
                self.text_device.receive_command(
                    instruction=inst_str,
                    value1=self.registers[1],
                    value2=self.registers[2],
                    value3=self.registers[3]
                )
            elif dev_type == 2:  # Graphical Display
                self.graphical_device.receive_command(
                    instruction=inst_str,
                    value1=self.registers[1],
                    value2=self.registers[2],
                    value3=self.registers[3]
                )
            
            self.write_flag = 0  # Command verwerkt en verzonden, vrij voor volgende OUT

        # --- READ SECTIE ---
        if self.read_flag == 0:
            if self.kbd_buffer:
                next_key = self.kbd_buffer.pop(0)
                self.registers[6] = next_key
                self.read_flag = 1
            else:
                self.registers[6] = 0  # NULL: geen input beschikbaar
                self.read_flag = 0

    def tick(self):
        """
        De achtergrond-tick op het mainboard.
        Geeft de aangesloten fysieke schermen een klokpuls om hun caches te renderen.
        """
        self.text_device.tick()
        self.graphical_device.tick()




# =========================================================================
# HARDWARE IO-CONTROLLER TECHNICAL SELF-TEST (POST)
# =========================================================================

if __name__ == "__main__":
    print("==================================================")
    print("  STERN-Z32G IO-CONTROLLER CHIP - DIAGNOSTIC POST ")
    print("==================================================")
    
    # We starten een onzichtbare master root voor de Tkinter context
    root = tk.Tk()
    root.withdraw() 
    
    print("[POST] STEP 1: Initialiseren IO-Controller & Peripherals...")
    ioc = IOController(root)
    print("[ OK ] Hardware componenten opgestart.")
    
    # --- TEST 1: Register Lezen/Schrijven ---
    print("[POST] STEP 2: Register Integriteitscontrole...")
    ioc.registers[1] = 0xAA
    if ioc.registers[1] == 0xAA:
        print("[ OK ] Register R/W stabiel.")
    else:
        print("[FAIL] Register corruptie gedetecteerd!"); sys.exit(1)
        
    # --- TEST 2: Bus Protocol & Write-Flag Trigger ---
    print("[POST] STEP 3: Bus Protocol & Write-Flag verificatie...")
    # Schrijf een commando (Type=1 (Karakter), Data='!', Inst=1 (Print))
    ioc.cpu_out(0, 1)
    ioc.cpu_out(1, ord('!'))
    ioc.cpu_out(5, 1) # Schrijven naar reg5 moet write_flag op 1 zetten
    
    if ioc.write_flag == 1:
        print("[ OK ] Write-flag correct getriggerd.")
    else:
        print("[FAIL] Write-flag trigger faalt!"); sys.exit(1)
        
    # Probeer nu nogmaals te schrijven; dit moet weigeren (False / Stall) wegens bezette controller
    if ioc.cpu_out(5, 1) == False:
        print("[ OK ] CPU Core Stall-beveiliging operationeel (Bus Locked).")
    else:
        print("[FAIL] Stall-beveiliging reageert niet!"); sys.exit(1)
        
    # Voer IOSYNC uit om de boel te flushen
    ioc.cpu_iosync()
    if ioc.write_flag == 0:
        print("[ OK ] IOSYNC wist de write-flag succesvol na verwerking.")
    else:
        print("[FAIL] IOSYNC heeft de write-flag niet vrijgegeven!"); sys.exit(1)

    # --- TEST 3: Toetsenbord Read-Flag Logica ---
    print("[POST] STEP 4: KBD Buffer & Read-Flag check...")
    ioc.kbd_buffer.append(65) # Simuleer indrukken van 'A' (ASCII 65)
    ioc.cpu_iosync()          # Laat de read-sectie dit oppikken
    
    if ioc.read_flag == 1 and ioc.registers[6] == 65:
        print("[ OK ] Toetsenbord-data correct doorgesluisd naar reg6 (Read-flag = 1).")
    else:
        print("[FAIL] Toetsenbord input logica defect!"); sys.exit(1)
        
    val = ioc.cpu_in(6) # CPU leest reg6 uit
    if ioc.read_flag == 0 and val == 65:
        print("[ OK ] CPU IN instructie reset de read-flag correct naar 0.")
    else:
        print("[FAIL] CPU IN instructie reset de read-flag niet!"); sys.exit(1)

    # --- TEST 4: Peripherals Visuele Bus Simulatie ---
    print("[POST] STEP 5: Genereren van testpatronen op de schermen via Bus-simulatie...")
    
    # Stuur welkomstboodschap naar TextDisplay via de officiële bus-instructies
    boodschap = "Inmos-Z32 IO-Controller POST: SUCCESS!\r\nLuistert nu actief op de bus..."
    for char in boodschap:
        ioc.cpu_out(0, 1)             # DevType = 1 (Text)
        ioc.cpu_out(1, ord(char))     # Char code
        ioc.cpu_out(5, 1)             # Instruction = 1 (Print)
        ioc.cpu_iosync()              # Verwerk direct
        
    # Teken een groen diagnostisch vierkant op het GraphicalDisplay via de bus
    # We plotten een kader van 100x100 pixels vanaf positie (50, 50)
    for x in range(50, 150):
        # Bovenste en onderste lijn
        for y in [50, 150]:
            ioc.cpu_out(0, 2)         # DevType = 2 (Grafisch)
            ioc.cpu_out(1, 21)        # Kleurcode (21mod8)
            ioc.cpu_out(2, x)         # X-coördinaat
            ioc.cpu_out(3, y)         # Y-coördinaat
            ioc.cpu_out(5, 2)         # Instruction = 2 (Plot)
            ioc.cpu_iosync()
            
    for y in range(50, 151):
        # Linker en rechter lijn
        for x in [50, 150]:
            ioc.cpu_out(0, 2)
            ioc.cpu_out(1, 12)      # kleus is 12MOD8
            ioc.cpu_out(2, x)
            ioc.cpu_out(3, y)
            ioc.cpu_out(5, 2)
            ioc.cpu_iosync()

    print("\n[ STATUS ] ALLE HARDWARE CHECKS: GESLAAGD!")
    print("[ INFO   ] Vensters blijven open ter visuele controle. Druk op Ctrl+C om te stoppen.")

    # Start een oneindige mainboard tick-loop zodat de schermen live blijven renderen
    def live_mainboard_ticks():
        ioc.tick()
        root.after(33, live_mainboard_ticks) # ~30 Hz verversing

    root.after(10, live_mainboard_ticks)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[HARDWARE] Systeem handmatig stopgezet. Tot ziens!")
        root.destroy()
        sys.exit(0)