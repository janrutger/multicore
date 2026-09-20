# CIUcontroller.py

from ExecuterZ32A import HardwareContext

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

    HIGH_WATERMARK = 15  # Minimaal aantal vrije cores vereist op worker voor ACK

    def __init__(self, cpu):
        self.cpu = cpu
        self.links = [None, None, None, None]  # Poorten: Link 0, 1, 2, 3
        self.rr_pointer = 0  # Houdt bij welke poort als laatste geprobeerd is
        

    def request_remote_context(self, task_pc, arg_reg, arg_val):
        """Scant aangesloten links volgens Round-Robin en biedt het
        instructie-pakket aan bij buren.

        Retourneert True (ACK) als een buur de taak heeft aangenomen, anders
        False (NACK).
        """
        packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc)
        num_links = len(self.links)

        # Scan 4 poorten vanaf de huidige Round-Robin pointer
        for i in range(num_links):
            port_id = (self.rr_pointer + i) % num_links
            link = self.links[port_id]

            if link is None:
                continue

            neighbor_ciu = link.get_other_end(self)
            if neighbor_ciu is None:
                continue

            # Bied het pakket aan de buur-CIU aan via jouw bestaande receive_packet
            ack = neighbor_ciu.receive_packet(packet)
            if ack:
                # ACK ontvangen! Zet de pointer klaar op de VOLGENDE poort voor de volgende taak
                self.rr_pointer = (port_id + 1) % num_links
                return True

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


    def receive_packet(self, packet):   
        cmd, arg_reg, arg_val, target_pc = packet

        if cmd == CMD_CONTEXT:
            # 1. High-Watermark check
            if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
                return False  # NACK!

            # 2. maak de HardwareContext aan met de overgedragen data-waarde!
            # from ExecuterZ32A import HardwareContext   # Lazzy import is not needed

            nieuwe_ctx = HardwareContext(
                self.cpu, source_reg=arg_reg, direct_value=arg_val
            )

            # 3. Configureer en activeer de thread op de ontvangende CPU
            nieuwe_ctx.PC = target_pc
            nieuwe_ctx.fsm_state = "FETCH"
            self.cpu.contexts.append(nieuwe_ctx)

        # === DEBUG PRINT BIJ SUCCESVOLLE INJECTIE (ACK) ===
            # ctx_id = len(self.cpu.contexts)
            # vrije_cores = len(self.cpu.free_cores)
            # print(
            #     f"\033[35m[CIU RX CPU{self.cpu.ID}] 🚀 Thread #{ctx_id}"
            #     f" geïnjecteerd | PC: {target_pc} | Arg R{arg_reg} ="
            #     f" {arg_val} | Cores over: {vrije_cores}\033[0m"
            # )


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