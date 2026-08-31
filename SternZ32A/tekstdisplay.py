import tkinter as tk
import sys

class textDisplay:
    def __init__(self, master_root=None):
        """
        De fysieke Karakter-Display Peripheral (24x80).
        Nu uitgerust met een hardware Command Cache (FIFO Queue).
        """
        # Als er geen master is, maken we een standalone root aan
        self.window = tk.Toplevel(master_root) if master_root else tk.Tk()
        self.window.title("SternZ32G - Character Display Peripheral")
        self.window.configure(bg="#111111")
        
        # Gekoppelde root onthouden voor shutdown-events
        self.master_root = master_root
        
        # Hardware shutdown interceptor (Zorgt dat sluiten de boel echt stopt!)
        self.window.protocol("WM_DELETE_WINDOW", self.hardware_power_down)
        
        # Fysieke specificaties (Standaard VT100 verhouding)
        self.rows = 24
        self.cols = 80
        
        # Hardware Command Cache (FIFO Queue voor de IO-controller)
        self.command_cache = []
        
        # Interne hardware-buffer (VRAM)
        self.screen_buffer = [[" " for _ in range(self.cols)] for _ in range(self.rows)]
        
        # Fysieke hardware cursor
        self.cursor_x = 0
        self.cursor_y = 0
        
        # GUI Component: Het retro groene tekstscherm
        self.text_area = tk.Text(
            self.window, 
            width=self.cols, 
            height=self.rows, 
            bg="#000000", 
            fg="#00ff00", 
            insertbackground="#00ff00",
            font=("Courier", 16, "bold"),
            padx=10,
            pady=10,
            state=tk.DISABLED
        )
        self.text_area.pack(padx=15, pady=15)
        
        # Eerste render van het lege scherm
        self.render_buffer()

    def hardware_power_down(self):
        """Fysieke noodstop: Vernietig de vensters en breek de event-loop af."""
        print("[HARDWARE] Power-down gedetecteerd op display peripheral. Systeem stopt...")
        if self.master_root:
            self.master_root.destroy()
        else:
            self.window.destroy()
        sys.exit(0)

    def receive_command(self, instruction, value1=None, value2=None, value3=None):
        """
        Interface voor de IO-Controller:
        Dempt een command-blok rechtstreeks in de hardware cache van dit device.
        """
        cmd_block = {
            "instruction": instruction,
            "value1": value1, 
            "value2": value2, 
            "value3": value3  
        }
        self.command_cache.append(cmd_block)

    def write_char(self, char):
        """
        De fysieke hardware-decoder voor de SternZ32G periferie.
        Verwerkt ASCII 13 nu direct als een gecombineerde CR + LF (New Line).
        """
        if isinstance(char, int):
            char_code = char
            char_str = chr(char)
        else:
            char_str = str(char)
            char_code = ord(char_str) if len(char_str) == 1 else 0

        # --- HARDWARE INTERCEPTOR VOOR STURINGSKARAKTERS ---
        
        # Gecombineerde CR + LF op ASCII 13 conform jouw specificatie
        if char_code == 13 or char_str == '\r':
            self.cursor_x = 0        # Carriage Return: naar het begin van de regel
            self.cursor_y += 1       # Line Feed: naar de volgende regel
            if self.cursor_y >= self.rows:
                self.scroll_screen() # Hardwarematige scroll indien buiten beeld
            return  # Hardware-actie voltooid, schrijf geen teken in VRAM

        # Optioneel: vang een losse ASCII 10 op als pure verticale sprong (zonder cursor_x = 0)
        if char_code == 10 or char_str == '\n':
            self.cursor_y += 1
            if self.cursor_y >= self.rows:
                self.scroll_screen()
            return

        # --- REGULIERE KARAKTER VERWERKING ---
        if self.cursor_y >= self.rows:
            self.scroll_screen()

        # Schrijf karakter naar de huidige cursorpositie in VRAM
        self.screen_buffer[self.cursor_y][self.cursor_x] = char_str
        self.cursor_x += 1

        # Hardwarematige automatische wrap-around bij het bereiken van de rechterrand
        if self.cursor_x >= self.cols:
            self.cursor_x = 0
            self.cursor_y += 1

        if self.cursor_y >= self.rows:
            self.scroll_screen()

    def scroll_screen(self):
        self.screen_buffer.pop(0)
        self.screen_buffer.append([" " for _ in range(self.cols)])
        self.cursor_y = self.rows - 1

    def clear_screen(self):
        self.screen_buffer = [[" " for _ in range(self.cols)] for _ in range(self.rows)]
        self.cursor_x = 0
        self.cursor_y = 0

    def move_cursor(self, x, y):
        try:
            nx = int(x) if x is not None else 0
            ny = int(y) if y is not None else 0
            self.cursor_x = max(0, min(nx, self.cols - 1))
            self.cursor_y = max(0, min(ny, self.rows - 1))
        except ValueError:
            pass 

    def render_buffer(self):
        try:
            self.text_area.config(state=tk.NORMAL)
            self.text_area.delete("1.0", tk.END)
            full_text = "\n".join(["".join(row) for row in self.screen_buffer])
            self.text_area.insert(tk.END, full_text)
            self.text_area.config(state=tk.DISABLED)
        except tk.TclError:
            pass # Voorkomt crashes tijdens het sluiten van het venster

    def tick(self):
        while self.command_cache:
            cmd = self.command_cache.pop(0) 
            inst = cmd["instruction"]
            
            if inst == "print":
                self.write_char(cmd["value1"])
            elif inst == "clear":
                self.clear_screen()
            elif inst == "move_cursor":
                self.move_cursor(cmd["value2"], cmd["value3"])
            
        self.render_buffer()


# =========================================================================
# GEÏSOLEERDE TEXT-DISPLAY PERIPHERAL TECHNICAL SELF-TEST
# =========================================================================

if __name__ == "__main__":
    print("[TEST] Initialiseren standalone tekstdisplay-test...")
    print("[INFO] Druk op Control-C in de terminal of sluit het venster om te stoppen.")
    
    root = tk.Tk()
    root.withdraw() 
    
    display = textDisplay(master_root=root)
    
    test_phase = 0
    char_index = 0
    test_string = "--- STERN Z32G HARDWARE \n TEXT DISPLAY SELF-TEST \r OPERATIONAL --- "

    def bus_clock_simulator():
        global test_phase, char_index
        
        try:
            # --- FASE 0: Schrijf de teststring ---
            if test_phase == 0:
                if char_index < len(test_string):
                    display.receive_command("print", value1=test_string[char_index])
                    char_index += 1
                else:
                    test_phase = 1
                    char_index = 0
            
            # --- FASE 1: Hardware Cursor Jump ---
            elif test_phase == 1:
                display.receive_command("move_cursor", value2=10, value3=5)
                display.receive_command("print", value1="[")
                display.receive_command("print", value1="X")
                display.receive_command("print", value1="]")
                test_phase = 2
                
            # --- FASE 2: Stress-test Auto-Scroll ---
            elif test_phase == 2:
                display.receive_command("move_cursor", value2=0, value3=23)
                fill_msg = "Dit is de bodem-regel. Volgende karakters moeten scrollen veroorzaken!    >>>>>>"
                for char in fill_msg:
                    display.receive_command("print", value1=char)
                test_phase = 3
                
            # --- FASE 3: Scroll-trigger ---
            elif test_phase == 3:
                extra_msg = "SCHERM SCROLLT NU!"
                for char in extra_msg:
                    display.receive_command("print", value1=char)
                test_phase = 4 
                print("[TEST] Technische testcyclus voltooid. Display luistert nu puur op de bus.")

            # Voer hardware TICK uit
            display.tick()
            
            # Altijd de klok blijven herhalen, ook na de testfases (zodat het scherm reresponsief blijft)
            root.after(100, bus_clock_simulator)
            
        except tk.TclError:
            # Als de root is vernietigd via de window sluitknop, breekt de loop hier stil af
            pass

    # Start de gesimuleerde hardware-klok
    root.after(500, bus_clock_simulator)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n[HARDWARE] Control-C ontvangen. Systeem wordt direct halt toegeroepen.")
        root.destroy()
        sys.exit(0)