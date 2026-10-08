# SternZ32A.py


import os
import sys
import time
import tkinter as tk
from assemblerV2 import assemble
from frontpanelZ32G import FrontPanel
from InmosZ32A import CPU
from IOcontroller import IOController
from CIUcontrollerV2r1 import ChannelLink
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

        # 2. Trek direct een ChannelLink tussen CPU0 (poort 0) en CPU1 (poort 0)
        ChannelLink(self.cpus[0].ciu, 0, self.cpus[1].ciu, 0) 
        ChannelLink(self.cpus[0].ciu, 1, self.cpus[2].ciu, 0)
        ChannelLink(self.cpus[0].ciu, 2, self.cpus[3].ciu, 0) 
        ChannelLink(self.cpus[0].ciu, 3, self.cpus[4].ciu, 0)   

        ChannelLink(self.cpus[1].ciu, 1, self.cpus[2].ciu, 1)
        ChannelLink(self.cpus[1].ciu, 2, self.cpus[3].ciu, 1)
        ChannelLink(self.cpus[1].ciu, 3, self.cpus[6].ciu, 1)

        # ChannelLink(self.cpus[2].ciu, 2, self.cpus[3].ciu, 2)
        # ChannelLink(self.cpus[2].ciu, 3, self.cpus[5].ciu, 2)

        # ChannelLink(self.cpus[2].ciu, 3, self.cpus[4].ciu, 1)

        # Uitbreiding naar 9 [0 .. 8] cpu's
        # ChannelLink(self.cpus[1].ciu, 2, self.cpus[5].ciu, 0)
        # ChannelLink(self.cpus[1].ciu, 3, self.cpus[6].ciu, 0)

        ChannelLink(self.cpus[4].ciu, 1, self.cpus[7].ciu, 2)
        ChannelLink(self.cpus[4].ciu, 2, self.cpus[2].ciu, 2)
        ChannelLink(self.cpus[4].ciu, 3, self.cpus[3].ciu, 2)
        



        # =========================================================================
        # --- DEBUG ROUTINE: TOON CIU TOPOLOGIE EN AFBREKEN ---
        # =========================================================================
        import sys

        print("\n==========================================================")
        print("           CIU TOPOLOGIE VERBINDINGEN DIAGNOSTIEK          ")
        print("==========================================================")

        for cpu in self.cpus:
            print(f"CPU {cpu.ID} (CIU Matrix):")
            actieve_links = 0

            for port_id, link in enumerate(cpu.ciu.links):
                if link is not None:
                    neighbor_ciu = link.get_other_end(cpu.ciu)

                    if neighbor_ciu is not None:
                        # Bepaal ook op welke poort de kabel bij de buur-CPU zit
                        neighbor_port = None
                        if (
                            link.endpoint_a
                            and link.endpoint_a[0] == neighbor_ciu
                        ):
                            neighbor_port = link.endpoint_a[1]
                        elif (
                            link.endpoint_b
                            and link.endpoint_b[0] == neighbor_ciu
                        ):
                            neighbor_port = link.endpoint_b[1]

                        print(
                            f"  [Poort {port_id}] ===> VERBONDEN MET ===> CPU"
                            f" {neighbor_ciu.cpu.ID} (Poort {neighbor_port})"
                        )
                        actieve_links += 1
                    else:
                        print(
                            f"  [Poort {port_id}] ===> Kabel aangesloten, maar"
                            " Geen Buur!"
                        )
                else:
                    print(f"  [Poort {port_id}] --- Niet aangesloten ---")

            if actieve_links == 0:
                print("  (WAARSCHUWING: Deze CPU heeft NUL actieve verbindingen!)")
            print("----------------------------------------------------------")

        print("==========================================================")
        print(" DIAGNOSTIEK VOLTOOID -                                   ")
        print("==========================================================\n")

        # sys.exit(0)  # Breek de uitvoering direct af


        self.show_log = False

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
        # Optellen van alle CPU-componenten
        tot_ucore = sum(cpu.time_ucore for cpu in self.cpus)
        tot_gc = sum(cpu.time_gc for cpu in self.cpus)
        tot_context = sum(cpu.time_context for cpu in self.cpus)
        tot_main = sum(cpu.time_main for cpu in self.cpus)

        sum_cpu_time = tot_ucore + tot_gc + tot_context + tot_main
        # Wat overblijft is de tijd besteed aan Tkinter GUI, event loops, canvas updates en OS overhead
        time_gui_and_overhead = max(0.0, totale_tijd - sum_cpu_time)

        """Drukt de eindrapportage af van het gehele systeem."""
        print("\n==========================================================")
        print("             SIMULATIE SUCCESVOL BEËINDIGD                ")
        print("==========================================================")
        print(f"Aantal CPU's: {self.num_cpus}")
        print(f"Totale Ticks: {self.totale_ticks}")
        print(f"Totale Tijd:  {totale_tijd:.4f} seconden")
        print(f"Snelheid:     {khz:.2f} kHz op de host machine.")
        print("==========================================================\n")

        print("\n==========================================================")
        print("             SternZ32 HARDWARE PROFILING REPORT            ")
        print("==========================================================")
        print(f"Totale Verstreken Tijd (Wall-Clock) : {totale_tijd:8.2f} s  (100.0%)")
        print("----------------------------------------------------------")
        print(f"1. uCore Compute Matrix             : {tot_ucore:8.2f} s  ({(tot_ucore/totale_tijd)*100:5.1f}%)")
        print(f"2. Garbage Collection (Wezen-check) : {tot_gc:8.2f} s  ({(tot_gc/totale_tijd)*100:5.1f}%)")
        print(f"3. Context Threads (Scheduler)      : {tot_context:8.2f} s  ({(tot_context/totale_tijd)*100:5.1f}%)")
        print(f"4. Main CPU Pipelines               : {tot_main:8.2f} s  ({(tot_main/totale_tijd)*100:5.1f}%)")
        print("----------------------------------------------------------")
        print(f"5. Tkinter GUI & Simulator Overhead : {time_gui_and_overhead:8.2f} s  ({(time_gui_and_overhead/totale_tijd)*100:5.1f}%)")
        print("==========================================================\n")

        # for cpu in self.cpus:
        #     print(
        #         f"\033[92m--- EINDSTATUS CPU {cpu.ID} (Vrije Cores:"
        #         f" {len(cpu.free_cores)}/32) ---"
        #     )
        #     print(f"  FSM State: {cpu.fsm_state} | PC: {cpu.PC}\033[0m")
        print("==========================================================")
        print("               PER-CPU STATUS & PROFILING                 ")
        print("==========================================================")
        for cpu in self.cpus:
            # Bereken totale executietijd op deze specifieke CPU
            cpu_total_time = cpu.time_ucore + cpu.time_gc + cpu.time_context + cpu.time_main
            safe_cpu_tot = cpu_total_time if cpu_total_time > 0 else 0.0001  # Voorkom DivisionByZero

            # Haal de maximale contexten veilig op (met fallback 0)
            max_ctx = getattr(cpu, 'max_contexts', 0)
            
            print(
                f"  s--- EINDSTATUS CPU {cpu.ID} (Vrije Cores:"
                f" {len(cpu.free_cores)}/32) ---"
            )
            print(
                f"  FSM State: {cpu.fsm_state:<13} | PC: {cpu.PC:<4} |"
                f" Max CTX: {max_ctx:<2} | Actieve Tijd: {cpu_total_time:6.2f} s"
            )
            print(
                f"  ├─ uCore Matrix     : {cpu.time_ucore:6.2f} s "
                f" ({(cpu.time_ucore/safe_cpu_tot)*100:5.1f}% van CPU-tijd)"
            )
            print(
                f"  ├─ GC (Wezen-check) : {cpu.time_gc:6.2f} s "
                f" ({(cpu.time_gc/safe_cpu_tot)*100:5.1f}% van CPU-tijd)"
            )
            print(
                f"  ├─ CTX Scheduler    : {cpu.time_context:6.2f} s "
                f" ({(cpu.time_context/safe_cpu_tot)*100:5.1f}% van CPU-tijd)"
            )
            print(
                f"  └─ Main Pipeline    : {cpu.time_main:6.2f} s "
                f" ({(cpu.time_main/safe_cpu_tot)*100:5.1f}% van CPU-tijd)\n"
            )
        print("==========================================================\n")


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