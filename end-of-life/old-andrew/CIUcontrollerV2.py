from ExecuterZ32AV2 import HardwareContext

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
    en bevat de hardwarematige 512-slot FIFO Mailbox Controller.
    """

    HIGH_WATERMARK = 15  # Minimaal aantal vrije cores vereist op worker voor ACK
    MAILBOX_DEPTH = 512  # Hardware capaciteit FIFO

    def __init__(self, cpu):
        self.cpu = cpu
        self.links = [None, None, None, None]  # Poorten: Link 0, 1, 2, 3
        self.rr_pointer = 0  # Houdt bij welke poort als laatste geprobeerd is

        # --- FIFO MAILBOX HARDWARE ---
        self.mailbox = [
            {
                "status": "FREE",
                "sender_cpuid": None,
                "msg_size": 0,
                "msg_tag": 0,       # <--- NIEUW: Opslag voor bericht-TAG / Event ID
                "data": []
            }
            for _ in range(self.MAILBOX_DEPTH)
        ]

        self.write_pointer = 0
        self.read_pointer = 0
        self.active_messages = 0

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
        """Scant aangesloten links volgens Round-Robin en biedt het
        instructie-pakket inclusief eigen CPU-ID (parent) aan bij buren.
        """
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
        """Stuurt een BOOT pakket over een specifieke link om een buur op te starten."""
        if 0 <= link_id < 4 and self.links[link_id] is not None:
            neighbor_ciu = self.links[link_id].get_other_end(self)
            if neighbor_ciu:
                my_id = getattr(self.cpu, 'ID', 0)
                packet = (CMD_BOOT, 0, 0, start_pc, my_id)
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

            if not neighbor_ciu.receive_packet(packet):
                return False

        return True

    # =========================================================================
    # NIEUWE MAILBOX INSTRUCTIES (ZENDER / WRITE API)
    # =========================================================================

    def msg_start(self, rx_msg_tag, ry_msg_size, parent_id):
        """
        msg_start Rx Ry
        Rx = Message TAG (Event Identifier)
        Ry = Message Size
        parent_id = Het Parent CPU ID waar het bericht automatisch naartoe gaat.
        """
        #neighbor_ciu = self._find_neighbor_ciu(parent_id)

        my_id = getattr(self.cpu, 'ID', 0)
        # 1. ROUTING CHECK: Is het bericht lokaal (voor de eigen CPU) of voor een externe buur?
        if parent_id == my_id:
            neighbor_ciu = self  # Lokaal bericht naar de eigen Mailbox!
        else:
            neighbor_ciu = self._find_neighbor_ciu(parent_id)
        
        if neighbor_ciu is None:
            raise RuntimeError(
                f"HARD EXIT [UNKNOWN_REMOTE_CPU]: Parent CPU {parent_id} is niet bekend "
                f"of niet rechtstreeks verbonden met CPU {getattr(self.cpu, 'ID', '?')}."
            )

        my_id = getattr(self.cpu, 'ID', 0)
        
        # Het pakket over de CIU-bus bevat: (CMD_MSG_RESERVE, sender_cpuid, msg_size, msg_tag)
        packet = (CMD_MSG_RESERVE, my_id, ry_msg_size, rx_msg_tag)
        remote_write_ptr = neighbor_ciu.receive_packet(packet)

        if remote_write_ptr is False or remote_write_ptr is None:
            self.cpu.status = 0
            return 0

        tx_id = self.next_tx_id
        self.next_tx_id = (self.next_tx_id % 65535) + 1

        self.tx_slots[tx_id] = {
            "remote_ciu": neighbor_ciu,
            "write_ptr": remote_write_ptr,
            "offset": 0
        }

        self.cpu.status = 1
        return tx_id

    def msg_write(self, ry_tx_slot_id, rx_value):
        """msg_write Ry Rx
        Ry = Tijdelijk tx_slotID, Rx = Datawaarde.
        """
        if ry_tx_slot_id not in self.tx_slots:
            self.cpu.status = 0
            return

        tx_info = self.tx_slots[ry_tx_slot_id]
        neighbor_ciu = tx_info["remote_ciu"]
        write_ptr = tx_info["write_ptr"]

        packet = (CMD_MSG_WRITE_DATA, write_ptr, rx_value, 0)
        success = neighbor_ciu.receive_packet(packet)

        if success:
            tx_info["offset"] += 1
            self.cpu.status = 1
        else:
            self.cpu.status = 0

    def msg_done(self, ry_tx_slot_id):
        """msg_done Ry
        Ry = Tijdelijk tx_slotID.
        """
        if ry_tx_slot_id not in self.tx_slots:
            self.cpu.status = 0
            return

        tx_info = self.tx_slots[ry_tx_slot_id]
        neighbor_ciu = tx_info["remote_ciu"]
        write_ptr = tx_info["write_ptr"]

        packet = (CMD_MSG_VALIDATE, write_ptr, 0, 0)
        neighbor_ciu.receive_packet(packet)

        del self.tx_slots[ry_tx_slot_id]
        self.cpu.status = 1

    # =========================================================================
    # NIEUWE MAILBOX INSTRUCTIES (ONTVANGER / READ API)
    # =========================================================================

    def msg_open(self):
        """msg_open Rx
        Retourneert gegenereerd read_slotID in register Rx bij succes.
        Sets status = True bij succes, False bij geen VALID bericht.
        """
        slot = self.mailbox[self.read_pointer]

        if slot["status"] != "VALID":
            self.cpu.status = 0
            return 0

        slot["status"] = "READING"

        rx_id = self.next_rx_id
        self.next_rx_id = (self.next_rx_id % 65535) + 1

        self.rx_slots[rx_id] = {
            "fifo_index": self.read_pointer,
            "offset": 0
        }

        self.read_pointer = (self.read_pointer + 1) % self.MAILBOX_DEPTH
        self.cpu.status = 1
        return rx_id

    # def msg_probe(self, ry_read_slot_id):
    #     """msg_probe Ry Rx
    #     Ry = Actieve read_slotID.
    #     Retourneert de Message TAG (in te stellen in Rx).
    #     """
    #     if ry_read_slot_id not in self.rx_slots:
    #         self.cpu.status = 0
    #         return 0

    #     fifo_idx = self.rx_slots[ry_read_slot_id]["fifo_index"]
    #     tag = self.mailbox[fifo_idx]["msg_tag"]  # <--- LEEST DE TAG UIT ENVELOP HEADER
    #     self.cpu.status = 1
    #     return tag
    # def msg_probe(self):
    #     """
    #     msg_probe Rx
    #     Inspecteert de header op de actuele read_pointer ZONDER de FIFO-status
    #     om te zetten naar READING of de read_pointer te verplaatsen.
        
    #     - Sets self.cpu.status = True indien VALID bericht aanwezig.
    #     - Sets self.cpu.status = False indien FIFO leeg of slot in WRITING.
    #     - Retourneert de msg_tag (voor opslag in Rx).
    #     """
    #     slot = self.mailbox[self.read_pointer]

    #     if slot["status"] != "VALID":
    #         self.cpu.status = False
    #         return 0

    #     self.cpu.status = True
    #     return slot["msg_tag"]
    def msg_probe(self, expected_tag):
        """
        msg_probe Rx
        Hardware Tag Match (Zero-Commit Inspection):
        - Controleert of er op de read_pointer een VALID bericht staat.
        - Vergelijkt de msg_tag in de header met expected_tag.
        - Sets self.cpu.status = True ALLEEN als het bericht VALID is én de TAG matcht.
        - Sets self.cpu.status = False in alle andere gevallen.
        - Consumeert NUL FIFO-slots en verandert de read_pointer NIET.
        """
        slot = self.mailbox[self.read_pointer]

        if slot["status"] == "VALID" and slot["msg_tag"] == expected_tag:
            self.cpu.status = True
            return True

        self.cpu.status = False
        return False

    def msg_read(self, ry_read_slot_id):
        """msg_read Ry Rx
        Ry = Actieve read_slotID.
        Retourneert het volgende datawoord op de data_offset.
        """
        if ry_read_slot_id not in self.rx_slots:
            self.cpu.status = 0
            return 0

        rx_info = self.rx_slots[ry_read_slot_id]
        fifo_idx = rx_info["fifo_index"]
        slot = self.mailbox[fifo_idx]

        if slot["status"] != "READING":
            self.cpu.status = 0
            return 0

        offset = rx_info["offset"]
        if offset >= len(slot["data"]):
            self.cpu.status = 0
            return 0

        val = slot["data"][offset]
        rx_info["offset"] += 1
        self.cpu.status = 1
        return val

    def msg_close(self, ry_read_slot_id):
        """msg_close Ry
        Ry = Actieve read_slotID.
        Zet slotstatus op FREE / EMPTY en ruimt de handle op.
        """
        if ry_read_slot_id not in self.rx_slots:
            self.cpu.status = 0
            return

        fifo_idx = self.rx_slots[ry_read_slot_id]["fifo_index"]

        self.mailbox[fifo_idx]["status"] = "FREE"
        self.mailbox[fifo_idx]["data"] = []
        self.mailbox[fifo_idx]["sender_cpuid"] = None
        self.mailbox[fifo_idx]["msg_size"] = 0
        self.mailbox[fifo_idx]["msg_tag"] = 0

        if self.active_messages > 0:
            self.active_messages -= 1

        del self.rx_slots[ry_read_slot_id]
        self.cpu.status = 1

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

        # --- MAILBOX INTERCONNECT AFHANDELING ---

        elif cmd == CMD_MSG_RESERVE:
            # arg_reg = sender_cpuid, arg_val = msg_size, target_pc = msg_tag
            sender_cpuid = arg_reg
            msg_size     = arg_val
            msg_tag      = target_pc  # <--- Het 4e element bevat de MSG_TAG!

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
            self.mailbox[reserved_ptr]["msg_tag"]      = msg_tag  # <--- TAG OPSLAAN
            self.mailbox[reserved_ptr]["data"]          = []

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

            # # === DEBUG LOGGING VOOR VALIDATED MAILBOX SLOT ===
            # cpu_id = getattr(self.cpu, 'ID', '?')
            # sender = slot['sender_cpuid']
            # tag    = slot['msg_tag']
            # size   = slot['msg_size']

            # # \033[36m geeft een heldere cyaan/cyan kleur in de terminal
            # print(
            #     f"\033[36m[CIU MAILBOX CPU {cpu_id}] 📩 Slot #{write_ptr:03d} "
            #     f"gevalideerd -> VALID | Afzender: CPU {sender} | "
            #     f"TAG: {tag} | Size: {size} datawoord(en)\033[0m"
            # )
            ### END DEBUG

            return True

        return False






# from ExecuterZ32AV2 import HardwareContext

# # --- CIU PACKET OPCODES ---
# CMD_CONTEXT = 1       # Remote Context Injection (RCONTEXT)
# CMD_BOOT = 2          # Remote CPU Boot / Wakeup
# CMD_SYNC = 3          # Barrier Query (ALLSYNC)
# CMD_MSG_RESERVE = 4   # Remote Mailbox: Reserveer schrijfslot
# CMD_MSG_WRITE_DATA = 5# Remote Mailbox: Schrijf datawoord
# CMD_MSG_VALIDATE = 6  # Remote Mailbox: Zet status op VALID


# class ChannelLink:
#     """Representeert een fysieke koperbaan/kabel op het mainboard
#     tussen twee CIU-poorten van verschillende CPU's.
#     """

#     def __init__(self, ciu_a, port_a, ciu_b, port_b):
#         self.endpoint_a = (ciu_a, port_a)
#         self.endpoint_b = (ciu_b, port_b)

#         # Koppel de kabel direct aan beide CIU-poorten
#         ciu_a.links[port_a] = self
#         ciu_b.links[port_b] = self

#     def get_other_end(self, current_ciu):
#         """Retourneert de CIU van de buur-CPU aan de andere kant van de kabel."""
#         if self.endpoint_a and self.endpoint_a[0] == current_ciu:
#             return self.endpoint_b[0]
#         elif self.endpoint_b and self.endpoint_b[0] == current_ciu:
#             return self.endpoint_a[0]
#         return None


# class CIU:
#     """Channel Interface Unit - Bevindt zich op het CPU-silicon.
#     Beheert 4 fysieke poorten (Link 0 t/m 3) voor communicatie met buren
#     en bevat de hardwarematige 512-slot FIFO Mailbox Controller.
#     """

#     HIGH_WATERMARK = 15  # Minimaal aantal vrije cores vereist op worker voor ACK
#     MAILBOX_DEPTH = 512  # Hardware capaciteit FIFO

#     def __init__(self, cpu):
#         self.cpu = cpu
#         self.links = [None, None, None, None]  # Poorten: Link 0, 1, 2, 3
#         self.rr_pointer = 0  # Houdt bij welke poort als laatste geprobeerd is

#         # --- FIFO MAILBOX HARDWARE ---
#         self.mailbox = [
#             {
#                 "status": "FREE",
#                 "sender_cpuid": None,
#                 "msg_size": 0,
#                 "data": []
#             }
#             for _ in range(self.MAILBOX_DEPTH)
#         ]

#         self.write_pointer = 0
#         self.read_pointer = 0
#         self.active_messages = 0

#         # Tijdelijke transactietabellen voor actieve handles
#         self.tx_slots = {}  # temp_slot_id -> { 'remote_ciu', 'write_ptr', 'offset' }
#         self.rx_slots = {}  # temp_read_id -> { 'fifo_index', 'offset' }

#         self.next_tx_id = 1
#         self.next_rx_id = 1

#     def _find_neighbor_ciu(self, target_cpu_id):
#         """Zoekt in de aangesloten fysieke links naar de CIU van de doel-CPU."""
#         for link in self.links:
#             if link is None:
#                 continue
#             neighbor = link.get_other_end(self)
#             if neighbor and hasattr(neighbor.cpu, 'ID') and neighbor.cpu.ID == target_cpu_id:
#                 return neighbor
#         return None

#     # =========================================================================
#     # BESTAANDE FUNCTIONALITEIT (RCONTEXT, RBOOT, ALLSYNC)
#     # =========================================================================

#     # def request_remote_context(self, task_pc, arg_reg, arg_val):
#     #     """Scant aangesloten links volgens Round-Robin en biedt het instructie-pakket aan."""
#     #     packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc)
#     #     num_links = len(self.links)

#     #     for i in range(num_links):
#     #         port_id = (self.rr_pointer + i) % num_links
#     #         link = self.links[port_id]

#     #         if link is None:
#     #             continue

#     #         neighbor_ciu = link.get_other_end(self)
#     #         if neighbor_ciu is None:
#     #             continue

#     #         ack = neighbor_ciu.receive_packet(packet)
#     #         if ack:
#     #             self.rr_pointer = (port_id + 1) % num_links
#     #             return True

#     #     return False
#     def request_remote_context(self, task_pc, arg_reg, arg_val):
#         """Scant aangesloten links volgens Round-Robin en biedt het
#         instructie-pakket inclusief eigen CPU-ID (parent) aan bij buren.
#         """
#         my_id = self.cpu.ID
#         # 5e element toegevoegd: my_id
#         packet = (CMD_CONTEXT, arg_reg, arg_val, task_pc, my_id)
#         num_links = len(self.links)

#         for i in range(num_links):
#             port_id = (self.rr_pointer + i) % num_links
#             link = self.links[port_id]

#             if link is None:
#                 continue

#             neighbor_ciu = link.get_other_end(self)
#             if neighbor_ciu is None:
#                 continue

#             ack = neighbor_ciu.receive_packet(packet)
#             if ack:
#                 self.rr_pointer = (port_id + 1) % num_links
#                 return True

#         return False

#     # def send_boot_remote(self, link_id, start_pc):
#     #     """Stuurt een BOOT pakket over een specifieke link om een buur op te starten."""
#     #     if 0 <= link_id < 4 and self.links[link_id] is not None:
#     #         neighbor_ciu = self.links[link_id].get_other_end(self)
#     #         if neighbor_ciu:
#     #             packet = (CMD_BOOT, 0, 0, start_pc)
#     #             return neighbor_ciu.receive_packet(packet)
#     #     return False
#     def send_boot_remote(self, link_id, start_pc):
#         if 0 <= link_id < 4 and self.links[link_id] is not None:
#             neighbor_ciu = self.links[link_id].get_other_end(self)
#             if neighbor_ciu:
#                 my_id = getattr(self.cpu, 'ID', 0)
#                 packet = (CMD_BOOT, 0, 0, start_pc, my_id)  # <--- my_id meegegeven
#                 return neighbor_ciu.receive_packet(packet)
#         return False

#     def are_all_neighbors_idle(self):
#         """Vraagt via een CMD_SYNC pakket aan alle aangesloten buren of ze 100% idle zijn."""
#         packet = (CMD_SYNC, 0, 0, 0)

#         for link in self.links:
#             if link is None:
#                 continue

#             neighbor_ciu = link.get_other_end(self)
#             if neighbor_ciu is None:
#                 continue

#             if not neighbor_ciu.receive_packet(packet):
#                 return False

#         return True

#     # =========================================================================
#     # NIEUWE MAILBOX INSTRUCTIES (ZENDER / WRITE API)
#     # =========================================================================

#     def msg_start(self, rx_remote_cpuid, ry_msg_size):
#         """msg_start Rx Ry
#         Rx = Remote CPU ID, Ry = Berichtsnoem / msg_size.
#         Retourneert het gegenereerde tijdelijke tx_slotID voor in register Ry.
#         """
#         neighbor_ciu = self._find_neighbor_ciu(rx_remote_cpuid)
        
#         # Harde fout als CPU Rx niet bekend of aangesloten is
#         if neighbor_ciu is None:
#             raise RuntimeError(
#                 f"HARD EXIT [UNKNOWN_REMOTE_CPU]: CPU {rx_remote_cpuid} is niet bekend "
#                 f"of niet rechtstreeks verbonden met CPU {getattr(self.cpu, 'ID', '?')}."
#             )

#         # Vraag de remote CIU om een write-pointer reservering
#         my_id = self.cpu.ID
#         packet = (CMD_MSG_RESERVE, my_id, ry_msg_size, 0)
#         remote_write_ptr = neighbor_ciu.receive_packet(packet)

#         if remote_write_ptr is False or remote_write_ptr is None:
#             self.cpu.status = False
#             return 0

#         # Maak lokaal tijdelijk tx_slotID aan
#         tx_id = self.next_tx_id
#         self.next_tx_id = (self.next_tx_id % 65535) + 1

#         self.tx_slots[tx_id] = {
#             "remote_ciu": neighbor_ciu,
#             "write_ptr": remote_write_ptr,
#             "offset": 0
#         }

#         self.cpu.status = True
#         return tx_id

#     def msg_write(self, ry_tx_slot_id, rx_value):
#         """msg_write Ry Rx
#         Ry = Tijdelijk tx_slotID, Rx = Datawaarde.
#         """
#         if ry_tx_slot_id not in self.tx_slots:
#             self.cpu.status = False
#             return

#         tx_info = self.tx_slots[ry_tx_slot_id]
#         neighbor_ciu = tx_info["remote_ciu"]
#         write_ptr = tx_info["write_ptr"]

#         # Stuur data naar remote CIU
#         packet = (CMD_MSG_WRITE_DATA, write_ptr, rx_value, 0)
#         success = neighbor_ciu.receive_packet(packet)

#         if success:
#             tx_info["offset"] += 1
#             self.cpu.status = True
#         else:
#             self.cpu.status = False

#     def msg_done(self, ry_tx_slot_id):
#         """msg_done Ry
#         Ry = Tijdelijk tx_slotID.
#         """
#         if ry_tx_slot_id not in self.tx_slots:
#             self.cpu.status = False
#             return

#         tx_info = self.tx_slots[ry_tx_slot_id]
#         neighbor_ciu = tx_info["remote_ciu"]
#         write_ptr = tx_info["write_ptr"]

#         # Informeer remote CIU dat het bericht VALID is
#         packet = (CMD_MSG_VALIDATE, write_ptr, 0, 0)
#         neighbor_ciu.receive_packet(packet)

#         # Ruim lokaal tijdelijk tx_slotID op
#         del self.tx_slots[ry_tx_slot_id]
#         self.cpu.status = True

#     # =========================================================================
#     # NIEUWE MAILBOX INSTRUCTIES (ONTVANGER / READ API)
#     # =========================================================================

#     def msg_open(self):
#         """msg_open Rx
#         Retourneert gegenereerd read_slotID in register Rx bij succes.
#         Sets status = True bij succes, False bij geen VALID bericht.
#         """
#         slot = self.mailbox[self.read_pointer]

#         if slot["status"] != "VALID":
#             self.cpu.status = False
#             return 0

#         # Reserveer bericht direct voor de lezer (status -> READING)
#         slot["status"] = "READING"

#         # Genereer tijdelijk read_slotID
#         rx_id = self.next_rx_id
#         self.next_rx_id = (self.next_rx_id % 65535) + 1

#         self.rx_slots[rx_id] = {
#             "fifo_index": self.read_pointer,
#             "offset": 0
#         }

#         # Verplaats globale read_pointer naar het volgende slot
#         self.read_pointer = (self.read_pointer + 1) % self.MAILBOX_DEPTH
#         self.cpu.status = True
#         return rx_id

#     def msg_probe(self, ry_read_slot_id):
#         """msg_probe Ry Rx
#         Ry = Actieve read_slotID.
#         Retourneert de msg_size (in te stellen in Rx).
#         """
#         if ry_read_slot_id not in self.rx_slots:
#             self.cpu.status = False
#             return 0

#         fifo_idx = self.rx_slots[ry_read_slot_id]["fifo_index"]
#         size = self.mailbox[fifo_idx]["msg_size"]
#         self.cpu.status = True
#         return size

#     def msg_read(self, ry_read_slot_id):
#         """msg_read Ry Rx
#         Ry = Actieve read_slotID.
#         Retourneert het volgende datawoord op de data_offset.
#         """
#         if ry_read_slot_id not in self.rx_slots:
#             self.cpu.status = False
#             return 0

#         rx_info = self.rx_slots[ry_read_slot_id]
#         fifo_idx = rx_info["fifo_index"]
#         slot = self.mailbox[fifo_idx]

#         if slot["status"] != "READING":
#             self.cpu.status = False
#             return 0

#         offset = rx_info["offset"]
#         if offset >= len(slot["data"]):
#             self.cpu.status = False
#             return 0

#         val = slot["data"][offset]
#         rx_info["offset"] += 1
#         self.cpu.status = True
#         return val

#     def msg_close(self, ry_read_slot_id):
#         """msg_close Ry
#         Ry = Actieve read_slotID.
#         Zet slotstatus op FREE / EMPTY en ruimt de handle op.
#         """
#         if ry_read_slot_id not in self.rx_slots:
#             self.cpu.status = False
#             return

#         fifo_idx = self.rx_slots[ry_read_slot_id]["fifo_index"]

#         # Geef FIFO slot vrij
#         self.mailbox[fifo_idx]["status"] = "FREE"
#         self.mailbox[fifo_idx]["data"] = []
#         self.mailbox[fifo_idx]["sender_cpuid"] = None
#         self.mailbox[fifo_idx]["msg_size"] = 0

#         if self.active_messages > 0:
#             self.active_messages -= 1

#         del self.rx_slots[ry_read_slot_id]
#         self.cpu.status = True

#     # =========================================================================
#     # CIU PAKKET AFHANDELING (INTERCONNECT RECEIVER)
#     # =========================================================================

#     def receive_packet(self, packet):
#         cmd, arg_reg, arg_val, target_pc, *extra = packet 

#         # if cmd == CMD_CONTEXT:
#         #     if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
#         #         return False
#         #     if self.cpu.fsm_state != "WAIT_FOR_WORK":
#         #         return False

#         #     nieuwe_ctx = HardwareContext(
#         #         self.cpu, source_reg=arg_reg, direct_value=arg_val
#         #     )
#         #     nieuwe_ctx.PC = target_pc
#         #     nieuwe_ctx.fsm_state = "FETCH"
#         #     self.cpu.contexts.append(nieuwe_ctx)
#         #     return True
#         if cmd == CMD_CONTEXT:
#             if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
#                 return False
#             if self.cpu.fsm_state != "WAIT_FOR_WORK":
#                 return False

#             # Ontvang het 5e element uit het pakket (het afzender/parent CPU ID)
#             # source_cpu_id = packet[4] if len(packet) > 4 else self.cpu.ID
#             source_cpu_id = extra[0] if extra else getattr(self.cpu, 'ID', 0)

#             nieuwe_ctx = HardwareContext(
#                 self.cpu,
#                 source_reg=arg_reg,
#                 direct_value=arg_val,
#                 parent_cpu_id=source_cpu_id  # <--- Geef de maker expliciet mee!
#             )
#             nieuwe_ctx.PC = target_pc
#             nieuwe_ctx.fsm_state = "FETCH"
#             self.cpu.contexts.append(nieuwe_ctx)
#             return True

#         elif cmd == CMD_BOOT:
#             if self.cpu.fsm_state not in ["WAIT_FOR_WORK", "HALT"]:
#                 return False
#             if len(self.cpu.free_cores) < self.HIGH_WATERMARK:
#                 self.cpu.fsm_state = "HALT"
#                 return False

#             # Als er een afzender CPU ID is meegegeven in extra, stel deze in als parent_id van de CPU
#             if extra:
#                 self.cpu.parent_id = extra[0]

#             self.cpu.PC = target_pc
#             self.cpu.fsm_state = "FETCH"
#             return True

#         elif cmd == CMD_SYNC:
#             return len(self.cpu.contexts) == 0

#         # --- MAILBOX INTERCONNECT AFHANDELING ---

#         elif cmd == CMD_MSG_RESERVE:
#             # arg_reg = sender_cpuid, arg_val = msg_size
#             sender_cpuid = arg_reg
#             msg_size = arg_val

#             # 1. Controleer op FIFO Overflow (> 512 berichten)
#             if self.active_messages >= self.MAILBOX_DEPTH:
#                 raise RuntimeError(
#                     f"HARD EXIT [FIFO_OVERFLOW]: FIFO Mailbox op CPU {getattr(self.cpu, 'ID', '?')} "
#                     f"is vol (> 512 berichten)!"
#                 )

#             # 2. Controleer op Read-Write Pointer Collision (abandoned slots)
#             if self.mailbox[self.write_pointer]["status"] != "FREE":
#                 raise RuntimeError(
#                     f"HARD EXIT [POINTER_COLLISION]: Pointer collision op CPU {getattr(self.cpu, 'ID', '?')}, "
#                     f"slot {self.write_pointer} is niet FREE!"
#                 )

#             # Reserveer het slot
#             reserved_ptr = self.write_pointer
#             self.mailbox[reserved_ptr]["status"] = "WRITING"
#             self.mailbox[reserved_ptr]["sender_cpuid"] = sender_cpuid
#             self.mailbox[reserved_ptr]["msg_size"] = msg_size
#             self.mailbox[reserved_ptr]["data"] = []

#             self.active_messages += 1
#             # Verhoog write_pointer voor de volgende msg_start
#             self.write_pointer = (self.write_pointer + 1) % self.MAILBOX_DEPTH

#             return reserved_ptr

#         elif cmd == CMD_MSG_WRITE_DATA:
#             # arg_reg = write_ptr, arg_val = value
#             write_ptr = arg_reg
#             value = arg_val

#             slot = self.mailbox[write_ptr]
#             if slot["status"] != "WRITING":
#                 return False

#             slot["data"].append(value)
#             return True

#         elif cmd == CMD_MSG_VALIDATE:
#             # arg_reg = write_ptr
#             write_ptr = arg_reg
#             slot = self.mailbox[write_ptr]

#             if slot["status"] == "WRITING":
#                 slot["status"] = "VALID"
#             return True

#         return False