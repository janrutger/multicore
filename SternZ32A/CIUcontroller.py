# CIUcontroller.py

# --- CIU PACKET OPCODES ---
CMD_CONTEXT = 1  # Remote Context Injection (RCONTEXT)
CMD_BOOT = 2  # Remote CPU Boot / Wakeup
CMD_SYNC = 3  # Barrier Query (ALLSYNC)


class ChannelLink:
    """Representeert een fysieke koperbaan/kabel op het mainboard

    tussen twee CIU-poorten van verschillende CPU's.
    """

    def __init__(self, ciu_a, port_a, ciu_b, port_b):
        self.endpoint_a = (ciu_a, port_a)
        self.endpoint_b = (ciu_b, port_b)

        # Koppel de kabel direct aan beide CIU-poorten
        ciu_a.links[port_a] = self
        ciu_b.links[port_b] = self

    def get_other_end(self, current_ciu):
        """Retourneert de CIU van de buur-CPU aan de andere kant van de kabel."""
        if self.endpoint_a and self.endpoint_a[0] == current_ciu:
            return self.endpoint_b[0]
        elif self.endpoint_b and self.endpoint_b[0] == current_ciu:
            return self.endpoint_a[0]
        return None


class CIU:
    """Channel Interface Unit - Bevindt zich op het CPU-silicon.

    Beheert 4 fysieke poorten (Link 0 t/m 3) voor communicatie met buren.
    """

    HIGH_WATERMARK = 10  # Minimaal aantal vrije cores vereist op worker voor ACK

    def __init__(self, cpu):
        self.cpu = cpu
        self.links = [None, None, None, None]  # Poorten: Link 0, 1, 2, 3
        
    # =========================================================================
    # ZENDER-ZIJDE (Requests versturen)
    # =========================================================================

    def request_remote_context(self, task_pc, arg_reg, arg_val):
        """Scant aangesloten links en biedt het instructie-pakket aan bij buren.

        Retourneert True (ACK) als een buur de taak heeft aangenomen, anders
        False (NACK).
        """
        packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc)

        for link in self.links:
        
            if link is None:
                continue

            neighbor_ciu = link.get_other_end(self)
            if neighbor_ciu is None:
                continue

            # Bied het pakket aan de buur-CIU aan
            ack = neighbor_ciu.receive_packet(packet)
            if ack:
                # print(f"[CIU CPU{self.cpu.ID}] ACK ontvangen! Remote context injected.")
                return True
            # else:     # Als deze buur NACK geeft, loopt de for-lus gewoon door naar de volgende link!
            #     # print(f"[CIU CPU{self.cpu.ID}] NACK ontvangen van alle buren.")
            #     return False

        return False  # NACK: Geen aangesloten buren of alle buren zitten vol

    def send_boot_remote(self, link_id, start_pc):
        """Stuurt een BOOT pakket over een specifieke link om een buur op te starten."""
        if 0 <= link_id < 4 and self.links[link_id] is not None:
            neighbor_ciu = self.links[link_id].get_other_end(self)
            if neighbor_ciu:
                packet = (CMD_BOOT, 0, 0, start_pc)
                return neighbor_ciu.receive_packet(packet)
        return False

    def are_all_neighbors_idle(self):
        """Vraagt via een CMD_SYNC pakket aan alle aangesloten buren of ze 100% idle zijn."""
        packet = (CMD_SYNC, 0, 0, 0)

        for link in self.links:
            if link is None:
                continue

            neighbor_ciu = link.get_other_end(self)
            if neighbor_ciu is None:
                continue

            # Als minstens 1 buur NACK geeft, rekent er nog iemand op die CPU
            if not neighbor_ciu.receive_packet(packet):
                return False

        return True

    # =========================================================================
    # ONTVANGER-ZIJDE (Binnenkomende pakketten afhandelen)
    # =========================================================================

    def receive_packet(self, packet):
        """Verwerkt een binnenkomend instructie-pakket van een buur-CPU."""
        cmd, arg_reg, arg_val, target_pc = packet

        if cmd == CMD_CONTEXT:
            # 1. High-Watermark check op deze lokale CPU
            if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
                return False  # NACK! Te weinig headroom op deze CPU

            # 2. STAP 1: Laad de overgedragen waarde in de HOOFD-registerfile van de CPU
            reg_core_id = self.cpu.free_cores.popleft()
            reg_core = self.cpu.cores[reg_core_id]
            reg_core.value = arg_val
            reg_core.coreStatus = "VALID"  # Data is gereed

            # Koppel deze core aan de hoofd-registerfile van deze CPU
            self.cpu.registers[arg_reg] = reg_core_id

            # 3. STAP 2: LAZY IMPORT om circular import te voorkomen
            from ExecuterZ32A import HardwareContext
            # Maak de HardwareContext aan (deze leest nu automatisch self.cpu.registers[arg_reg]!)
            nieuwe_ctx = HardwareContext(self.cpu, arg_reg)


            # 4. STAP 3: Stel de start-PC van de thread in op de HEAT_WORKER
            nieuwe_ctx.PC = target_pc
            nieuwe_ctx.fsm_state = "FETCH"

            # 5. Voeg de thread toe aan de actieve contexts van deze CPU
            self.cpu.contexts.append(nieuwe_ctx)

            # # === DEBUG PRINT BIJ SUCCESVOLLE INJECTIE (ACK) ===
            # ctx_id = len(self.cpu.contexts)
            # vrije_cores = len(self.cpu.free_cores)
            # print(
            #     f"\033[35m[CIU RX CPU{self.cpu.ID}] 🚀 Thread #{ctx_id}"
            #     f" geïnjecteerd | PC: {target_pc} | Arg R{arg_reg} ="
            #     f" {arg_val} | Cores over: {vrije_cores}\033[0m"
            # )

            reg_core.coreStatus = 'IDLE'    # return the core on next GC run

            return True  # ACK!

        elif cmd == CMD_BOOT:
            # Wek de hoofd-pijplijn van de CPU op en stel zijn PC in
            self.cpu.PC = target_pc
            self.cpu.fsm_state = "FETCH"
            return True

        elif cmd == CMD_SYNC:
            # Geef READY (True) alleen als deze CPU 100% idle is (alle 32 cores vrij)
            # return len(self.cpu.free_cores) == 32
            return len(self.cpu.contexts) == 0

        return False