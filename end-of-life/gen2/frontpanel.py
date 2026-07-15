# frontpanel.py
import tkinter as tk

class FrontPanel:
    def __init__(self, num_cores=16):
        self.root = tk.Tk()
        self.root.title("STERN-ATX Frontpaneel")
        self.root.configure(bg="#1e1e1e") # Mooie donkere retro look
        
        self.leds = []
        
        # Maak een 4x4 matrix van LEDs
        for i in range(num_cores):
            row = i // 4
            col = i % 4
            
            # Frame voor de layout
            frame = tk.Frame(self.root, bg="#1e1e1e", padx=10, pady=10)
            frame.grid(row=row, column=col)
            
            # De LED zelf (een Canvas cirkel)
            canvas = tk.Canvas(frame, width=30, height=30, bg="#1e1e1e", highlightthickness=0)
            canvas.pack()
            # Teken een initiële rode cirkel
            circle = canvas.create_oval(2, 2, 28, 28, fill="red")
            
            # Label voor het Core ID
            label = tk.Label(frame, text=f"Core {i}", fg="white", bg="#1e1e1e", font=("Courier", 8))
            label.pack()
            
            self.leds.append((canvas, circle))
            
    def update_cores(self, cores):
        """Update de kleuren van de LEDs op basis van de werkelijke Ucore status."""
        color_map = {
            'IDLE': '#ff0000',     # Fel rood
            'WORKING': '#ffaa00',  # Oranje
            'VALID': '#00ff00'     # Groen
        }
        
        for i, core in enumerate(cores):
            canvas, circle = self.leds[i]
            # Haal de status op uit jouw Ucore object
            color = color_map.get(core.coreStatus, 'gray')
            canvas.itemconfig(circle, fill=color)
            
        # Verwerk de Tkinter events direct (zorgt voor realtime update zonder root.mainloop)
        self.root.update_idletasks()
        self.root.update()
        
    def close(self):
        self.root.destroy()