
import tkinter as tk
import sys


# =========================================================================
# HARDWARE GRAPHICAL DISPLAY PERIPHERAL (480x640)
# =========================================================================

class GraphicalDisplay:
    def __init__(self, master_root):
        """Fysieke Grafische Peripheral met eigen VRAM en hardware clipping."""
        self.window = tk.Toplevel(master_root)
        self.window.title("SternZ32G - Graphical Display Peripheral")
        self.window.configure(bg="#1a1a1a")
        
        self.width = 640
        self.height = 480
        self.command_cache = []
        
        # --- HARDWARE PALETTE LOOKUP TABLE (LUT) ---
        # Map de integer-waarde uit het CPU-register naar een Tkinter kleur
        self.palette = {
            0: "#000000",  # Zwart
            1: "#ffffff",  # Wit
            2: "#ff0000",  # Rood (dit matched nu je test-programma!)
            3: "#00ff00",  # Groen
            4: "#0000ff",  # Blauw
            5: "#ffff00",  # Geel
            6: "#ff00ff",  # Magenta
            7: "#00ffff"   # Cyan
        }

        # Teken-oppervlak
        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height, bg="#000000", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

    def receive_command(self, instruction, value1, value2, value3):
        self.command_cache.append({
            "instruction": instruction,
            "value1": value1,  # Kleur (id of gecodeerd)
            "value2": value2,  # X
            "value3": value3   # Y
        })

    def tick(self):
        """Verwerkt gecachte plots en past strikte hardware-clipping toe."""
        while self.command_cache:
            cmd = self.command_cache.pop(0)
            inst = cmd["instruction"]
            
            if inst == "clear":
                self.canvas.delete("all")
                
            elif inst == "plot":
                x = cmd["value2"]
                y = cmd["value3"]
                
                # --- HARDWARE CLIPPING ---
                # Waardes buiten het fysieke 480x640 bereik worden genegeerd en weggegooid
                if 0 <= x < self.width and 0 <= y < self.height:
                    # Bepaal kleur (Zet om naar hex-kleur indien nodig, default groen)
                    # color = "#ffffff" if cmd["value1"] == 1 else "#00ff00"
                    color = self.palette[cmd["value1"]%8]       # Modulo 8 om binnen het kleur pallete te blijven
                    # Teken een 1x1 pixel via een micro-rechthoek
                    self.canvas.create_rectangle(x, y, x+1, y+1, outline=color, fill=color)