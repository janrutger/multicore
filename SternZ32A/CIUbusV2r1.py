from ExecuterZ32AV2r2 import HardwareContext

# --- CIU PACKET OPCODES ---
CMD_CONTEXT = 1          # Remote Context Injection (RCONTEXT)
CMD_BOOT = 2             # Remote CPU Boot / Wakeup
CMD_SYNC = 3             # Barrier Query (ALLSYNC)
CMD_MSG_RESERVE = 4      # Remote Mailbox: Reserveer schrijfslot
CMD_MSG_WRITE_DATA = 5   # Remote Mailbox: Schrijf datawoord
CMD_MSG_VALIDATE = 6     # Remote Mailbox: Zet status op VALID


class CIUBus:
    """Representeert de gedeelde CIU Interconnect Bus op het mainboard.
    Iedere CPU koppelt zijn CIU aan deze bus.
    """

    def __init__(self):
        self.nodes = {}  # Map van cpu_id -> ciu_instance
        self.rr_pointer = 0    # Hardware Round-Robin pointer voor eerlijke werklastverdeling

    def attach(self, ciu):
        """Koppelt een CIU aan de bus."""
        cpu_id = getattr(ciu.cpu, 'ID', None)
        if cpu_id is not None:
            self.nodes[cpu_id] = ciu

    def send_packet(self, target_cpu_id, packet):
        """Punt-naar-punt transmissie via de bus."""
        target_ciu = self.nodes.get(target_cpu_id)
        if target_ciu:
            return target_ciu.receive_packet(packet)
        return False

    def request_round_robin_context(self, sender_ciu, packet):
        """ECHTE ROUND-ROBIN BUS ARBITER:
        Scant alle beschikbare CPU's op de bus, roterend vanaf de laatst succesvolle positie.
        """
        if not self.nodes:
            return False

        cpu_ids = sorted(self.nodes.keys())
        num_nodes = len(cpu_ids)
        my_id = getattr(sender_ciu.cpu, 'ID', None)

        # Scant exact 1 ronde over de bus vanaf de huidige rr_pointer
        for i in range(num_nodes):
            current_idx = (self.rr_pointer + i) % num_nodes
            target_id = cpu_ids[current_idx]

            # Sla de zendende CPU zelf over
            if target_id == my_id:
                continue

            target_ciu = self.nodes[target_id]
            
            # Probeer de context aan te bieden
            if target_ciu.receive_packet(packet):
                # SUCCES! Schuif de Round-Robin pointer op naar de volgende CPU voor de volgende beurt
                self.rr_pointer = (current_idx + 1) % num_nodes
                return True

        return False  # Geen enkele CPU op de bus heeft capaciteit/vrije cores

    def broadcast_sync(self, sender_ciu):
        """Broadcast vraag naar alle ANDERE CPU's op de bus voor ALLSYNC."""
        packet = (CMD_SYNC, 0, 0, 0)
        for cpu_id, ciu in self.nodes.items():
            if ciu == sender_ciu:
                continue
            if not ciu.receive_packet(packet):
                return False  # Zodra één CPU niet idle is, faalt de sync
        return True


class CIU:
    """Channel Interface Unit - Bevindt zich op het CPU-silicon.
    Verbonden met de centrale CIUBus voor directe P2P communicatie
    en voorzien van de hardwarematige 512-slot FIFO Mailbox Controller.
    """

    HIGH_WATERMARK = 15  # Minimaal aantal vrije cores vereist op worker voor ACK
    MAILBOX_DEPTH = 512  # Hardware capaciteit FIFO

    def __init__(self, cpu, bus=None):
        self.cpu = cpu
        self.bus = bus
        if self.bus:
            self.bus.attach(self)

        # --- FIFO MAILBOX HARDWARE ---
        self.mailbox = [
            {
                "status": "FREE",
                "sender_cpuid": None,
                "msg_size": 0,
                "msg_tag": 0,
                "data": []
            }
            for _ in range(self.MAILBOX_DEPTH)
        ]

        self.write_pointer = 0
        self.read_pointer = 0
        self.active_messages = 0

        # Flow Control
        self.rx_flow_blocked = False
        self.WATERMARK_HIGH = 511
        self.WATERMARK_LOW = 256

        # Transactietabellen
        self.tx_slots = {}
        self.rx_slots = {}

        self.next_tx_id = 1
        self.next_rx_id = 1

    def attach_bus(self, bus):
        """Sluit de CIU achteraf aan op een bus."""
        self.bus = bus
        self.bus.attach(self)

    # =========================================================================
    # BUS-GEBASEERDE FUNCTIONALITEIT (RCONTEXT, RBOOT, ALLSYNC)
    # =========================================================================

    # def request_remote_context(self, task_pc, arg_reg, arg_val, target_cpu_id=None):
    #     """Injecteert een context op een specifieke doel-CPU of zoekt op de bus."""
    #     my_id = getattr(self.cpu, 'ID', 0)
    #     packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc, my_id)

    #     if not self.bus:
    #         return False

    #     # Als er een specifiek target_cpu_id is opgegeven
    #     if target_cpu_id is not None:
    #         return self.bus.send_packet(target_cpu_id, packet)

    #     # Anders: Broadcast/Round-Robin over beschikbare knopen op de bus
    #     for cpu_id, target_ciu in self.bus.nodes.items():
    #         if cpu_id == my_id:
    #             continue
    #         if target_ciu.receive_packet(packet):
    #             return True

    #     return False
    def request_remote_context(self, task_pc, arg_reg, arg_val, target_cpu_id=None):
        my_id = getattr(self.cpu, 'ID', 0)
        packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc, my_id)

        if not self.bus:
            return False

        # 1. Specifieke adressering (Punt-naar-Punt)
        if target_cpu_id is not None:
            return self.bus.send_packet(target_cpu_id, packet)

        # 2. Automatische verdeling via de Echte Round-Robin Bus Arbiter
        return self.bus.request_round_robin_context(self, packet)

    def send_boot_remote(self, target_cpu_id, start_pc):
        """Boot een specifieke CPU via zijn ID over de bus."""
        if self.bus and target_cpu_id in self.bus.nodes:
            my_id = getattr(self.cpu, 'ID', 0)
            packet = (CMD_BOOT, 0, 0, start_pc, my_id)
            return self.bus.send_packet(target_cpu_id, packet)
        return False

    def are_all_neighbors_idle(self):
        """Controleert via de bus of ALLE andere CPU's in ruststand zijn."""
        if not self.bus:
            return True
        return self.bus.broadcast_sync(self)

    # =========================================================================
    # MAILBOX INSTRUCTIES (ZENDER / WRITE API)
    # =========================================================================

    def msg_start(self, rx_msg_tag, ry_msg_size, parent_id):
        my_id = getattr(self.cpu, 'ID', 0)

        if parent_id == my_id:
            neighbor_ciu = self
        else:
            if not self.bus or parent_id not in self.bus.nodes:
                raise RuntimeError(
                    f"HARD EXIT [UNKNOWN_REMOTE_CPU]: Target CPU {parent_id} "
                    f"is niet aangesloten op de CIU bus."
                )
            neighbor_ciu = self.bus.nodes[parent_id]

        packet = (CMD_MSG_RESERVE, my_id, ry_msg_size, rx_msg_tag)
        remote_write_ptr = neighbor_ciu.receive_packet(packet)

        if remote_write_ptr is False or remote_write_ptr is None:
            return False, 0

        tx_id = self.next_tx_id
        self.next_tx_id = (self.next_tx_id % 65535) + 1

        self.tx_slots[tx_id] = {
            "remote_ciu": neighbor_ciu,
            "write_ptr": remote_write_ptr,
            "offset": 0
        }

        return True, tx_id

    def msg_write(self, ry_tx_slot_id, rx_value):
        if ry_tx_slot_id not in self.tx_slots:
            return False

        tx_info = self.tx_slots[ry_tx_slot_id]
        neighbor_ciu = tx_info["remote_ciu"]
        write_ptr = tx_info["write_ptr"]

        packet = (CMD_MSG_WRITE_DATA, write_ptr, rx_value, 0)
        success = neighbor_ciu.receive_packet(packet)

        if success:
            tx_info["offset"] += 1
            return True

        return False

    def msg_done(self, ry_tx_slot_id):
        if ry_tx_slot_id not in self.tx_slots:
            return False

        tx_info = self.tx_slots[ry_tx_slot_id]
        neighbor_ciu = tx_info["remote_ciu"]
        write_ptr = tx_info["write_ptr"]

        packet = (CMD_MSG_VALIDATE, write_ptr, 0, 0)
        success = neighbor_ciu.receive_packet(packet)

        if success:
            del self.tx_slots[ry_tx_slot_id]
            return True

        return False

    # =========================================================================
    # MAILBOX INSTRUCTIES (ONTVANGER / READ API)
    # =========================================================================

    def msg_open(self):
        slot = self.mailbox[self.read_pointer]

        if slot["status"] != "VALID":
            return False, 0

        slot["status"] = "READING"

        rx_id = self.next_rx_id
        self.next_rx_id = (self.next_rx_id % 65535) + 1

        self.rx_slots[rx_id] = {
            "fifo_index": self.read_pointer,
            "offset": 0
        }

        self.read_pointer = (self.read_pointer + 1) % self.MAILBOX_DEPTH
        return True, rx_id

    def msg_probe(self, expected_tag):
        slot = self.mailbox[self.read_pointer]
        if slot["status"] == "VALID" and slot["msg_tag"] == expected_tag:
            return True
        return False

    def msg_read(self, ry_read_slot_id):
        if ry_read_slot_id not in self.rx_slots:
            return False, 0

        rx_info = self.rx_slots[ry_read_slot_id]
        fifo_idx = rx_info["fifo_index"]
        slot = self.mailbox[fifo_idx]

        if slot["status"] != "READING":
            return False, 0

        offset = rx_info["offset"]
        if offset >= len(slot["data"]):
            return False, 0

        val = slot["data"][offset]
        rx_info["offset"] += 1
        return True, val

    def msg_close(self, ry_read_slot_id):
        if ry_read_slot_id not in self.rx_slots:
            return False

        fifo_idx = self.rx_slots[ry_read_slot_id]["fifo_index"]

        self.mailbox[fifo_idx]["status"] = "FREE"
        self.mailbox[fifo_idx]["data"] = []
        self.mailbox[fifo_idx]["sender_cpuid"] = None
        self.mailbox[fifo_idx]["msg_size"] = 0
        self.mailbox[fifo_idx]["msg_tag"] = 0

        if self.active_messages > 0:
            self.active_messages -= 1

        if self.rx_flow_blocked and self.active_messages <= self.WATERMARK_LOW:
            self.rx_flow_blocked = False

            cpu_id = getattr(self.cpu, 'ID', '?')
            print(
                f"\033[32m[CIU INFO    CPU {cpu_id}] ✅ Low Watermark bereikt "
                f"({self.active_messages}/{self.MAILBOX_DEPTH} slots bezet). "
                f"Flow Control opgeheven: inkomende berichten worden weer toegelaten!\033[0m"
            )

        del self.rx_slots[ry_read_slot_id]
        return True

    # =========================================================================
    # CIU PAKKET AFHANDELING
    # =========================================================================

    def receive_packet(self, packet):
        cmd, arg_reg, arg_val, target_pc, *extra = packet 

        if cmd == CMD_CONTEXT:
            if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
                return False
            if self.cpu.fsm_state != "WAIT_FOR_WORK":
                return False

            source_cpu_id = extra[0] if extra else getattr(self.cpu, 'ID', 0)
            nieuwe_ctx = HardwareContext(
                self.cpu,
                source_reg=arg_reg,
                direct_value=arg_val,
                parent_cpu_id=source_cpu_id
            )
            nieuwe_ctx.PC = target_pc
            nieuwe_ctx.fsm_state = "FETCH"
            self.cpu.contexts.append(nieuwe_ctx)
            return True

        elif cmd == CMD_BOOT:
            if self.cpu.fsm_state not in ["WAIT_FOR_WORK", "HALT"]:
                return False
            if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
                self.cpu.fsm_state = "HALT"
                return False

            if extra:
                self.cpu.parent_id = extra[0]

            self.cpu.PC = target_pc
            self.cpu.fsm_state = "FETCH"
            return True

        elif cmd == CMD_SYNC:
            return len(self.cpu.contexts) == 0

        elif cmd == CMD_MSG_RESERVE:
            sender_cpuid = arg_reg
            msg_size     = arg_val
            msg_tag      = target_pc

            if self.rx_flow_blocked:
                return False

            if self.active_messages >= self.WATERMARK_HIGH:
                self.rx_flow_blocked = True

                # --- DIAGNOSTISCHE WAARSCHUWING ---
                cpu_id = getattr(self.cpu, 'ID', '?')
                print(
                    f"\033[33m[CIU WARNING CPU {cpu_id}] ⚠️ High Watermark bereikt "
                    f"({self.active_messages}/{self.MAILBOX_DEPTH} slots bezet). "
                    f"Flow Control geactiveerd: inkomende berichten worden tijdelijk gestald!\033[0m"
                )

            if self.active_messages >= self.MAILBOX_DEPTH:
                raise RuntimeError(f"HARD EXIT [FIFO_OVERFLOW]: CPU {getattr(self.cpu, 'ID', '?')}")

            if self.mailbox[self.write_pointer]["status"] != "FREE":
                raise RuntimeError(f"HARD EXIT [POINTER_COLLISION]: CPU {getattr(self.cpu, 'ID', '?')}")

            reserved_ptr = self.write_pointer
            self.mailbox[reserved_ptr]["status"]       = "WRITING"
            self.mailbox[reserved_ptr]["sender_cpuid"] = sender_cpuid
            self.mailbox[reserved_ptr]["msg_size"]     = msg_size
            self.mailbox[reserved_ptr]["msg_tag"]      = msg_tag
            self.mailbox[reserved_ptr]["data"]         = []

            self.active_messages += 1
            self.write_pointer = (self.write_pointer + 1) % self.MAILBOX_DEPTH

            return reserved_ptr

        elif cmd == CMD_MSG_WRITE_DATA:
            write_ptr = arg_reg
            value     = arg_val

            slot = self.mailbox[write_ptr]
            if slot["status"] != "WRITING":
                return False

            slot["data"].append(value)
            return True

        elif cmd == CMD_MSG_VALIDATE:
            write_ptr = arg_reg
            slot = self.mailbox[write_ptr]

            if slot["status"] == "WRITING":
                slot["status"] = "VALID"

            return True

        return False