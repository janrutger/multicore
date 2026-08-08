
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
        
        # --- HARDWARE PALETTE LOOKUP TABLE (LUT) - 16 KLEUREN ---
        # Standaard 16-kleuren palet (CGA / EGA geïnspireerd, geoptimaliseerd voor warmtekaarten)
        self.palette = {
            0:  "#000000",  # Zwart (Koud / Achtergrond)
            1:  "#000080",  # Donkerblauw
            2:  "#0000FF",  # Blauw
            3:  "#0080FF",  # Lichtblauw
            4:  "#00FFFF",  # Cyan
            5:  "#00FF80",  # Turkoois / Mint
            6:  "#00FF00",  # Felgroen
            7:  "#80FF00",  # Geelgroen
            8:  "#FFFF00",  # Geel
            9:  "#FFC800",  # Goud / Oranjegeel
            10: "#FF8000",  # Oranje
            11: "#FF4000",  # Roodoranje
            12: "#FF0000",  # Felrood
            13: "#FF0080",  # Roze / Magenta
            14: "#FF80FF",  # Lichtmagenta
            15: "#FFFFFF"   # Helderwit (Maximale hitte)
        }

        # Teken-oppervlak
        self.canvas = tk.Canvas(self.window, width=self.width, height=self.height, bg="#000000", highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

    def receive_command(self, instruction, value1, value2, value3):
        self.command_cache.append({
            "instruction": instruction,
            "value1": value1,  # Kleur (0 t/m 15)
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
                if 0 <= x < self.width and 0 <= y < self.height:
                    # Modulo 16 dwingt de index af binnen het 16-kleuren palet
                    color_idx = cmd["value1"] % 15
                    color = self.palette[color_idx]
                    
                    # Teken een 1x1 pixel (of groter blok op basis van je pixel-schaal)
                    self.canvas.create_rectangle(x, y, x+4, y+4, outline=color, fill=color)

# class GraphicalDisplay:
#     def __init__(self, master_root):
#         """Fysieke Grafische Peripheral met eigen VRAM en hardware clipping."""
#         self.window = tk.Toplevel(master_root)
#         self.window.title("SternZ32G - Graphical Display Peripheral")
#         self.window.configure(bg="#1a1a1a")
        
#         self.width = 640
#         self.height = 480
#         self.command_cache = []
        
#         # --- HARDWARE PALETTE LOOKUP TABLE (LUT) ---
#         # Map de integer-waarde uit het CPU-register naar een Tkinter kleur
#         self.palette = {
#             0: "#000000",  # Zwart
#             1: "#ffffff",  # Wit
#             2: "#ff0000",  # Rood (dit matched nu je test-programma!)
#             3: "#00ff00",  # Groen
#             4: "#0000ff",  # Blauw
#             5: "#ffff00",  # Geel
#             6: "#ff00ff",  # Magenta
#             7: "#00ffff"   # Cyan
#         }

#         # Teken-oppervlak
#         self.canvas = tk.Canvas(self.window, width=self.width, height=self.height, bg="#000000", highlightthickness=0)
#         self.canvas.pack(padx=10, pady=10)

#     def receive_command(self, instruction, value1, value2, value3):
#         self.command_cache.append({
#             "instruction": instruction,
#             "value1": value1,  # Kleur (id of gecodeerd)
#             "value2": value2,  # X
#             "value3": value3   # Y
#         })

#     def tick(self):
#         """Verwerkt gecachte plots en past strikte hardware-clipping toe."""
#         while self.command_cache:
#             cmd = self.command_cache.pop(0)
#             inst = cmd["instruction"]
            
#             if inst == "clear":
#                 self.canvas.delete("all")
                
#             elif inst == "plot":
#                 x = cmd["value2"]
#                 y = cmd["value3"]
                
#                 # --- HARDWARE CLIPPING ---
#                 # Waardes buiten het fysieke 480x640 bereik worden genegeerd en weggegooid
#                 if 0 <= x < self.width and 0 <= y < self.height:
#                     # Bepaal kleur (Zet om naar hex-kleur indien nodig, default groen)
#                     # color = "#ffffff" if cmd["value1"] == 1 else "#00ff00"
#                     color = self.palette[cmd["value1"]%8]       # Modulo 8 om binnen het kleur pallete te blijven
#                     # Teken een 1x1 pixel via een micro-rechthoek
#                     self.canvas.create_rectangle(x, y, x+1, y+1, outline=color, fill=color)