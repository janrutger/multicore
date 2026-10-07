class CIU:
    # ... __init__, links, en helper-methoden blijven exact gelijk ...

    # =========================================================================
    # MAILBOX INSTRUCTIES (ZENDER / WRITE API)
    # =========================================================================

    def msg_start(self, rx_msg_tag, ry_msg_size, parent_id):
        neighbor_ciu = self._find_neighbor_ciu(parent_id)
        
        if neighbor_ciu is None:
            raise RuntimeError(
                f"HARD EXIT [UNKNOWN_REMOTE_CPU]: Parent CPU {parent_id} is niet bekend "
                f"of niet rechtstreeks verbonden met CPU {getattr(self.cpu, 'ID', '?')}."
            )

        my_id = getattr(self.cpu, 'ID', 0)
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
        neighbor_ciu.receive_packet(packet)

        del self.tx_slots[ry_tx_slot_id]
        return True

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

        del self.rx_slots[ry_read_slot_id]
        return True