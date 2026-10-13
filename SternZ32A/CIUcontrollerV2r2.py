from ExecuterZ32AV2r2 import HardwareContext

# --- CIU PACKET OPCODES ---
CMD_CONTEXT = 1          # Remote Context Injection (RCONTEXT)
CMD_BOOT = 2             # Remote CPU Boot / Wakeup
CMD_SYNC = 3             # Barrier Query (ALLSYNC)
CMD_MSG_RESERVE = 4      # Remote Mailbox: Reserveer schrijfslot
CMD_MSG_WRITE_DATA = 5   # Remote Mailbox: Schrijf datawoord
CMD_MSG_VALIDATE = 6     # Remote Mailbox: Zet status op VALID


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
    Beheert 4 fysieke poorten (Link 0 t/m 3) voor communicatie met buren
    en bevat de hardwarematige 512-slot FIFO Mailbox Controller met Flow Control.
    """

    HIGH_WATERMARK = 15     # Minimaal aantal vrije cores vereist op worker voor ACK
    MAILBOX_DEPTH = 512     # Hardware capaciteit FIFO
    
    # --- NIEUWE WATERMARK GRENZEN VOOR FLOW CONTROL ---
    WATERMARK_HIGH = 511    # Sluit de kraan als er 511 of meer slots bezet zijn
    WATERMARK_LOW  = 256     # Open de kraan pas weer als we onder de 256 zakken (voorkomt thrashing)

    def __init__(self, cpu):
        self.cpu = cpu
        self.links = [None, None, None, None]  # Poorten: Link 0, t/m 3
        self.rr_pointer = 0  # Houdt bij welke poort als laatste geprobeerd is

        # --- FIFO MAILBOX HARDWARE ---
        self.mailbox = [
            {
                "status": "FREE",
                "sender_cpuid": None,
                "msg_size": 0,
                "msg_tag": 0,       # Opslag voor bericht-TAG / Event ID
                "data": []
            }
            for _ in range(self.MAILBOX_DEPTH)
        ]

        self.write_pointer = 0
        self.read_pointer = 0
        self.active_messages = 0

        # --- NIEUWE FLOW CONTROL BLOKKEERVLAG ---
        self.rx_flow_blocked = False  # True als de FIFO te vol is en ingaande requests weigert

        # Tijdelijke transactietabellen voor actieve handles
        self.tx_slots = {}  # temp_slot_id -> { 'remote_ciu', 'write_ptr', 'offset' }
        self.rx_slots = {}  # temp_read_id -> { 'fifo_index', 'offset' }

        self.next_tx_id = 1
        self.next_rx_id = 1

    def _find_neighbor_ciu(self, target_cpu_id):
        """Zoekt in de aangesloten fysieke links naar de CIU van de doel-CPU."""
        for link in self.links:
            if link is None:
                continue
            neighbor = link.get_other_end(self)
            if neighbor and hasattr(neighbor.cpu, 'ID') and neighbor.cpu.ID == target_cpu_id:
                return neighbor
        return None

    # =========================================================================
    # BESTAANDE FUNCTIONALITEIT (RCONTEXT, RBOOT, ALLSYNC)
    # =========================================================================

    def request_remote_context(self, task_pc, arg_reg, arg_val):
        my_id = getattr(self.cpu, 'ID', 0)
        packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc, my_id)
        num_links = len(self.links)

        for i in range(num_links):
            port_id = (self.rr_pointer + i) % num_links
            link = self.links[port_id]

            if link is None:
                continue

            neighbor_ciu = link.get_other_end(self)
            if neighbor_ciu is None:
                continue

            ack = neighbor_ciu.receive_packet(packet)
            if ack:
                self.rr_pointer = (port_id + 1) % num_links
                return True

        return False

    def send_boot_remote(self, link_id, start_pc):
        if 0 <= link_id < 4 and self.links[link_id] is not None:
            neighbor_ciu = self.links[link_id].get_other_end(self)
            if neighbor_ciu:
                my_id = getattr(self.cpu, 'ID', 0)
                packet = (CMD_BOOT, 0, 0, start_pc, my_id)
                return neighbor_ciu.receive_packet(packet)
        return False

    def are_all_neighbors_idle(self):
        packet = (CMD_SYNC, 0, 0, 0)
        for link in self.links:
            if link is None:
                continue
            neighbor_ciu = link.get_other_end(self)
            if neighbor_ciu is None:
                continue
            if not neighbor_ciu.receive_packet(packet):
                return False
        return True

    # =========================================================================
    # MAILBOX INSTRUCTIES (ZENDER / WRITE API)
    # =========================================================================

    def msg_start(self, rx_msg_tag, ry_msg_size, parent_id):
        """
        msg_start Rx Ry
        Geeft (True, tx_id) bij succes, of (False, 0) bij een volle FIFO (Stall trigger).
        """
        my_id = getattr(self.cpu, 'ID', 0)

        if parent_id == my_id:
            neighbor_ciu = self
        else:
            neighbor_ciu = self._find_neighbor_ciu(parent_id)
        
        if neighbor_ciu is None:
            raise RuntimeError(
                f"HARD EXIT [UNKNOWN_REMOTE_CPU]: Parent CPU {parent_id} is niet bekend "
                f"of niet rechtstreeks verbonden met CPU {my_id}."
            )

        # Pakket verzenden naar de receptionist (CIU van buur of zichzelf)
        packet = (CMD_MSG_RESERVE, my_id, ry_msg_size, rx_msg_tag)
        remote_write_ptr = neighbor_ciu.receive_packet(packet)

        # --- FLOW CONTROL AFHANDELING ---
        if remote_write_ptr is False:
            # Ontvanger zit boven High Watermark -> Geef False terug zodat de CPU stalt!
            return False, 0

        # TX-slot registreren
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
        """
        Sluit het gelezen slot en controleert direct of we onder de 
        Low Watermark zijn gezakt om de flow-block op te heffen.
        """
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

        # --- LOW WATERMARK CHECK ---
        if self.rx_flow_blocked and self.active_messages <= self.WATERMARK_LOW:
            self.rx_flow_blocked = False  # Hef de blokkade op!

            cpu_id = getattr(self.cpu, 'ID', '?')
            print(
                f"\033[32m[CIU INFO    CPU {cpu_id}] ✅ Low Watermark bereikt "
                f"({self.active_messages}/{self.MAILBOX_DEPTH} slots bezet). "
                f"Flow Control opgeheven: inkomende berichten worden weer toegelaten!\033[0m"
            )

        del self.rx_slots[ry_read_slot_id]
        return True

    # =========================================================================
    # CIU PAKKET AFHANDELING (INTERCONNECT RECEIVER)
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

        # --- MAILBOX INTERCONNECT & WATERMARK CONTROLE ---

        elif cmd == CMD_MSG_RESERVE:
            sender_cpuid = arg_reg
            msg_size     = arg_val
            msg_tag      = target_pc

            # 1. ALS DE FLOW BLOCKED IS (High Watermark bereikt), WEIGER DIRECT (NACK -> STALL)
            if self.rx_flow_blocked:
                return False

            # 2. ALS WE HET HIGH WATERMARK RAKEN TIJDENS DEZE RESERVERING
            if self.active_messages >= self.WATERMARK_HIGH:
                self.rx_flow_blocked = True  # Blokkeer verdere inkomende berichten

                # --- DIAGNOSTISCHE WAARSCHUWING ---
                cpu_id = getattr(self.cpu, 'ID', '?')
                print(
                    f"\033[33m[CIU WARNING CPU {cpu_id}] ⚠️ High Watermark bereikt "
                    f"({self.active_messages}/{self.MAILBOX_DEPTH} slots bezet). "
                    f"Flow Control geactiveerd: inkomende berichten worden tijdelijk gestald!\033[0m"
                )

            if self.active_messages >= self.MAILBOX_DEPTH:
                raise RuntimeError(
                    f"HARD EXIT [FIFO_OVERFLOW]: FIFO Mailbox op CPU {getattr(self.cpu, 'ID', '?')} is vol (> 512 berichten)!"
                )

            if self.mailbox[self.write_pointer]["status"] != "FREE":
                raise RuntimeError(
                    f"HARD EXIT [POINTER_COLLISION]: Pointer collision op CPU {getattr(self.cpu, 'ID', '?')}, slot {self.write_pointer} is niet FREE!"
                )

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