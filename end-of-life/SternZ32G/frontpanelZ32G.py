
import tkinter as tk

class FrontPanel:
    def __init__(self, master_root, num_cores=32):
        """
        Geïntegreerd Frontpaneel dat meelift op de gedeelde root van het mainboard.
        Dit voorkomt Tkinter-overhead en multi-loop crashes.
        """
        self.root = master_root
        
        # Optioneel: Je kunt de titel van de root hier overschrijven of aanpassen
        self.root.title("STERN-Z32 Central Dashboard & Frontpanel")
        
        self.leds = []
        
        # Dynamische grid-indeling (bijv. 8 kolommen breed voor 32 cores)
        kolommen = 8
        
        # Bouw de LED-matrix op binnen de meegegeven root
        for i in range(num_cores):
            row = i // kolommen
            col = i % kolommen
            
            # Frame voor de layout van deze specifieke core LED
            frame = tk.Frame(self.root, bg="#1e1e1e", padx=10, pady=10)
            frame.grid(row=row, column=col)
            
            # De LED zelf (een Canvas cirkel)
            canvas = tk.Canvas(frame, width=30, height=30, bg="#1e1e1e", highlightthickness=0)
            canvas.pack()
            
            # Teken de initiële rode (IDLE) cirkel
            circle = canvas.create_oval(2, 2, 28, 28, fill="#ff0000", outline="#3a3a3a")
            
            # Label voor het Core ID
            label = tk.Label(frame, text=f"Core {i:02d}", fg="#888888", bg="#1e1e1e", font=("Courier", 8))
            label.pack()
            
            self.leds.append((canvas, circle))
            
    def update_cores(self, cores):
        """Update de kleuren van de LEDs live op basis van de werkelijke uCore statussen."""
        color_map = {
            'IDLE': '#ff0000',     # Fel rood
            'WORKING': '#ffaa00',  # Oranje/Geel
            'VALID': '#00ff00'     # Groen (Data staat klaar!)
        }
        
        for i, core in enumerate(cores):
            # Veiligheidsklepje voor het geval de CPU minder cores heeft dan het paneel
            if i >= len(self.leds):
                break
                
            canvas, circle = self.leds[i]
            color = color_map.get(core.coreStatus, '#555555')
            canvas.itemconfig(circle, fill=color)