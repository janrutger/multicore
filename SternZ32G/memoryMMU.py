"""
========================================================================================
INMOS-Z32 CPU MEMORY MAP (Virtueel / Logisch Adresbereik)
========================================================================================

Adresbereik (Decimaal)  | Geheugensegment   | Toegang    | Omschrijving & Kenmerken
----------------------------------------------------------------------------------------
0 tot progEnd           | Program (Page0)   | Read-Only  | Executeerbare machinecode (ROM).
(bijv. 0 - 1023)        |                   |            | Alleen te laden via write_rom().
                        |                   |            |
progEnd + 1 t/m sharedEnd| Shared Memory    | Read/Write | Gedeelde data-ruimte tussen CPU's.
(bijv. 1024 - 2047)     |                   |            | Beveiligd met cyclus-locking (64w).
                        |                   |            |
sharedEnd + 1 t/m memEnd| Private Memory    | Read/Write | Afgeschermd privégeheugen per CPU.
(bijv. 2048 - 2559)     |                   |            | Unieke offset per cpu_id (Lazy Page).
----------------------------------------------------------------------------------------
Totale omvang: memEnd + 1 woorden (bijv. 2560 woorden)

Dynamische Grenzen & Formules:
  - progEnd   = Page0 - 1
  - sharedEnd = progEnd + Shared
  - memEnd    = sharedEnd + Private
========================================================================================
"""



class MMU:

    def __init__(self, Page0=1024, Private=512, Shared=1024, block_size=64):
        self.progMem = [0] * Page0
        self.sharedMem = [0] * Shared

        self.privatedPages = {}
        self.privatePageSize = Private

        self.progEnd = Page0 - 1
        self.sharedEnd = self.progEnd + Shared
        self.memEnd = self.sharedEnd + Private

        # Blok-level bus-locking per klokcyclus
        self.block_size = block_size
        self.cycle_locks = {}           # Onthoudt {block_id: cpu_id} voor de HUIDIGE klokcyclus

    def create_private_page(self, cpu_id):
        if cpu_id not in self.privatedPages:
            self.privatedPages[cpu_id] = [0] * self.privatePageSize

    def memSize(self):
        return self.memEnd + 1

    def tick(self):
        """Wordt aan het einde van elke centrale klokcyclus aangeroepen.

        Wist alle bus-reservaties zodat in de volgende cyclus iedereen weer
        vrije toegang heeft.
        """
        self.cycle_locks.clear()

    def memRead(self, adres, cpu_id=0):
        if adres < 0 or adres > self.memEnd:
            raise ValueError(
                f"Adres {adres} valt buiten het totale geheugenbereik (0 -"
                f" {self.memEnd})"
            )

        # 1. Read-Only Program memory
        if adres <= self.progEnd:
            return self.progMem[adres]

        # 2. Shared memory
        elif adres <= self.sharedEnd:
            offset = adres - (self.progEnd + 1)
            return self.sharedMem[offset]

        # 3. Private memory
        else:
            offset = adres - (self.sharedEnd + 1)
            if cpu_id not in self.privatedPages:
                self.create_private_page(cpu_id)
            return self.privatedPages[cpu_id][offset]

    def memWrite(self, value, adres, cpu_id=0):
        if adres < 0 or adres > self.memEnd:
            raise ValueError(
                f"Adres {adres} valt buiten het totale geheugenbereik (0 -"
                f" {self.memEnd})"
            )

        # 1. Program memory is Read-Only!
        if adres <= self.progEnd:
            raise PermissionError(
                f"Poging tot schrijven naar Read-Only programmageheugen op"
                f" adres {adres}"
            )

        # 2. Shared memory met automatische cyclus-locking
        elif adres <= self.sharedEnd:
            offset = adres - (self.progEnd + 1)
            block_id = offset // self.block_size
            owner = self.cycle_locks.get(block_id)

            # Als het blok vrij is of al geclaimd door DEZE cpu in deze cyclus
            if owner is None or owner == cpu_id:
                self.cycle_locks[block_id] = cpu_id
                self.sharedMem[offset] = value
                return "OK"
            else:
                # Een ANDERE CPU was in deze klokcyclus al eerder met schrijven naar dit blok!
                return "STALL"

        # 3. Private memory schrijven
        else:
            offset = adres - (self.sharedEnd + 1)
            if cpu_id not in self.privatedPages:
                self.create_private_page(cpu_id)
            self.privatedPages[cpu_id][offset] = value
            return "OK"

    def write_rom(self, code_words, start_adres=0):
        """Bypasst de Read-Only beveiliging om geassembleerde machinecode

        in het programmageheugen te laden voor de start van de simulatie.
        """
        if (
            start_adres < 0
            or (start_adres + len(code_words) - 1) > self.progEnd
        ):
            raise ValueError(
                f"Programma (grootte {len(code_words)}) past niet binnen"
                f" het progMem-bereik (0 t/m {self.progEnd})"
            )

        for i, word in enumerate(code_words):
            self.progMem[start_adres + i] = word