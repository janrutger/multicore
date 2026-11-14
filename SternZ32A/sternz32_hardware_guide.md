# SternZ32 Hardware Guide (Inmos-Z32 Architectuur)

Welkom bij de officiële hardwaregids voor het **SternZ32** parallelle computersysteem (gebaseerd op de **Inmos-Z32** architectuur). Dit document beschrijft de interne werking van het moederbord, de CPU-cores, de 32-core uCore-rekenmatrix, de Memory Management Unit (MMU), de Channel Interface Unit (CIU) en de randapparatuur.

---

## Inhoudsopgave

1. [Systeemoverzicht & Moederbordarchitectuur](#1-systeemoverzicht--moederbordarchitectuur)
2. [De Inmos-Z32 CPU & Executiepijplijn](#2-de-inmos-z32-cpu--executiepijplijn)
3. [De uCore Matrix & Microcode-architectuur](#3-de-ucore-matrix--microcode-architectuur)
4. [Memory Management Unit (MMU) & Geheugenindeling](#4-memory-management-unit-mmu--geheugenindeling)
5. [Channel Interface Unit (CIU) & Inter-CPU Bus](#5-channel-interface-unit-ciu--inter-cpu-bus)
6. [I/O-Controller & Randapparatuur](#6-io-controller--randapparatuur)
7. [Instructie-encoding & Machinecodeformaat](#7-instructie-encoding--machinecodeformaat)

---

## 1. Systeemoverzicht & Moederbordarchitectuur

Het **SternZ32 Mainboard** (`SternZ32Mainboard`) is een synchroon geklokt multi-CPU platform dat schaalt van 1 tot $N$ Inmos-Z32 CPU's.

```
+-------------------------------------------------------------------------+
|                        STERN-Z32 MAINBOARD                              |
|                                                                         |
|  +-------------------+   +-------------------+   +-------------------+  |
|  |   CPU 0 (Master)  |   |   CPU 1 (Worker)  |   |   CPU N (Worker)  |  |
|  |  - 32 uCores      |   |  - 32 uCores      |   |  - 32 uCores      |  |
|  |  - 10 Registers   |   |  - 10 Registers   |   |  - 10 Registers   |  |
|  |  - On-Chip CIU    |   |  - On-Chip CIU    |   |  - On-Chip CIU    |  |
|  +----+----+----+----+   +----+---------+----+   +----+---------+----+  |
|       |    |    |             |         |             |         |       |
|       |    |    +-------------+---------+-------------+---------+       |
|       |    |                  |                                         |
|       |    |          [ CIU Interconnect Bus ] (P2P, RR-Arbiter, FIFO)  |
|       |    |                                                            |
|       |    +------------------+-----------------------+                 |
|       |                       |                                         |
|       |               [ Centrale MMU Bus ] (Page0, Shared, Private)     |
|       |                                                                 |
|  +----+--------------+                                                  |
|  |  IO-Controller    |---> Graphical Display (640x480, 16-kleuren)      |
|  |  (reg0 .. reg6)   |---> Character Display (80x24 VT100)              |
|  +-------------------+---> Keyboard Buffer (ASCII)                      |
|                                                                         |
|  [ FrontPanel LED Matrix ] (Live status van 32 uCores op CPU 0)         |
+-------------------------------------------------------------------------+
```

### Standaard Mainboard-configuratie
* **Kloksnelheid & Batching:** De centrale klok (`gameloop`) voert standaard **50 klokcycli per GUI-frame** (`cycles_per_frame = 50`) uit. Binnen elke klokcyclus worden alle actieve CPU's synchroon getikt, gevolgd door een `mmu.tick()` om bus-locks vrij te geven.
* **Bootgedrag:** **CPU 0** is de Master CPU en start na reset direct in de `FETCH`-status op `PC = 0`. Alle overige CPU's (`CPU 1..N`) starten in de energiezuinige `WAIT_FOR_WORK`-status totdat zij via de CIU-bus worden gewekt (`RBOOT` of `RCONTEXT`).
* **I/O-koppeling:** De `IOController` is standaard gekoppeld aan Master **CPU 0**. In de standaard mainboard-configuratie staat het grafische display ingeschakeld (`xyplot=True`), terwijl het tekstscherm en toetsenbord standaard uitgeschakeld zijn (`tekst=False, kbd=False`). De schermverversing (`io_controller.tick()`) draait op een prescaler van **1 op 5000** hoofdkloktikken (`IO_PRESCALER = 5000`).
* **FrontPanel:** Een visuele 8×4 LED-matrix toont live de status van de 32 uCores van CPU 0:
  * **Rood (`#ff0000`):** `IDLE` (vrij in de pool)
  * **Oranje/Geel (`#ffaa00`):** `WORKING` (bezig met microcode-executie)
  * **Groen (`#00ff00`):** `VALID` (resultaat staat gereed in de core)
* **Data-breedte:** Onderliggend werken registers en geheugenwoorden met willekeurige integer-precisie (Python integers). Specifieke bitwise- en cryptografische instructies (`ROTL32`, `RND32`) dwingen expliciet een **32-bit resultaatbreedte** (`0xFFFFFFFF`) af.

---

## 2. De Inmos-Z32 CPU & Executiepijplijn

Elke Inmos-Z32 CPU is een hybride processor die traditionele instructie-executie combineert met **dataflow-achtige register-abstractie** en **hardware-multithreading**.

### 2.1 Architecturale Registers & Pointer-model
Een CPU (en elke sub-context) beschikt over **10 registers** (`0` t/m `9`). In tegenstelling tot klassieke CPU's slaan deze registers **geen directe datawaarden** op, maar een **uCore-ID pointer** (`0..31`) naar de rekenunit die de waarde beheert.

| Index | Naam | Hardware-functie |
| :--- | :--- | :--- |
| `0` | **`I`** | **Index Register** (vaste hardware-koppeling voor `LDX` en `STX`) |
| `1` – `9` | **`A`, `B`, `C`, `K`, `L`, `M`, `X`, `Y`, `Z`** | Algemene registers (wijzen naar uCore-ID's) |

*(Opmerking: Een hardware stack-pointer `SP` wordt geïnitialiseerd op het hoogste geheugenadres, maar hardwarematige stack-instructies zoals `PUSH`/`POP` zijn nog niet geïmplementeerd.)*

### 2.2 De Klokcyclus (4-Fasige CPU Tick)
Binnen één enkele `cpu.tick()` voert elke CPU vier stappen uit:
1. **uCore Matrix Tick:** Alle 32 uCores voeren één micro-instructie uit.
2. **Hardware Garbage Collection ("Wezen-check"):** De CPU scant alle registers van de hoofd-CPU, alle actieve sub-contexten, `last_test_core` en de `arg1`/`arg2`-afhankelijkheden van `WORKING` cores. Elke `VALID` uCore waarnaar geen enkele actieve referentie meer verwijst, wordt direct teruggezet naar `IDLE` en toegevoegd aan de vrije wachtrij (`free_cores`).
3. **Sub-context Scheduler (Round-Robin):** Actieve lokale threads (`HardwareContext`) worden round-robin ingepland. Om sub-contexten te versnellen worden `FETCH` en `DECODE` binnen dezelfde tik gecombineerd uitgevoerd, gevolgd door `EXECUTE` in de volgende tik.
4. **Hoofd-CPU Pijplijn:** De hoofd-CPU doorloopt een 3-fasige Finite State Machine (`FETCH` $\rightarrow$ `DECODE` $\rightarrow$ `EXECUTE`), één fase per kloktik.

### 2.3 Hardware Contexts & High-Watermark Beveiliging
* Met `CONTEXT Rx, target_pc` start de hoofd-CPU een parallelle `HardwareContext` met een eigen `PC`, eigen statusvlag en eigen registerset. De waarde van `Rx` wordt gekopieerd naar een nieuw gealloceerde uCore in register `Rx` van de sub-context.
* **High-Watermark (`15` vrije cores):** Om deadlock door uCore-uitputting te voorkomen, weigert de hardware nieuwe `CONTEXT`- en `RCONTEXT`-aanvragen zodra er minder dan **15 vrije uCores** (`len(free_cores) < 15`) beschikbaar zijn. De statusvlag wordt dan op `0` gezet (`FAIL`).
* Sub-contexten mogen zelf geen nieuwe sub-contexten spawnen (dit genereert een `Hardware Fault`).

---

## 3. De uCore Matrix & Microcode-architectuur

Elke Inmos-Z32 CPU bevat een matrix van **32 asynchrone uCores** (`Ucore`). Zodra een reken- of laadinstructie wordt gedecodeerd, claimt de CPU een vrije uCore, koppelt deze aan het doelregister en gaat direct door met de volgende instructie zonder te wachten tot de berekening klaar is (**non-blocking dispatch**).

### 3.1 Interne uCore Architectuur
Een uCore beschikt over minimale interne hardware:
* **`V` (Value):** Primair invoer- en uitvoerregister (bevat het eindresultaat zodra `coreStatus == 'VALID'`).
* **`W` (Work):** Secundair operandregister voor ALU-operaties.
* **`T` (Transfer):** Accumulator en doorgangsregister vanuit de hoofd-CPU.
* **`Status`:** Interne boolean vlag voor vergelijkingen en micro-branches.
* **`sign_v` / `sign_w`:** Hardware-latches die het oorspronkelijke teken (`< 0`) van invoeroperanden vasthouden.
* **`upc`:** Interne Micro-Program Counter.

### 3.2 Hardware Interlock & Synchronisatie (`valid_v` / `valid_w`)
Data-afhankelijkheden worden volledig in hardware opgelost. Wanneer een uCore een microprogramma start (bijv. `add`), voert zij eerst `valid_v` en `valid_w` uit. De uCore controleert of de bron-uCores (`arg1` en `arg2`) al de status `'VALID'` hebben. Zolang een bron-core nog `'WORKING'` is, blokkeert de ontvangende uCore automatisch op die micro-instructie zonder de hoofd-CPU te vertragen.

### 3.3 Microcode ROM (`MICROCODE_ROM`)
Alle ALU- en testinstructies zijn geïmplementeerd als microprogramma's in de `MICROCODE_ROM`:
* **Data & Conversie:** `ldv` (laad transfer naar V), `ld` (kopieer tussen cores), `stv`, `status`.
* **Rekenkunde:** `add`, `sub`, `mul` (single-cycle hardware vermenigvuldiging; `slow_mul` is enkel aanwezig voor testdoeleinden), `div` (deling door 0 geeft veilig `0` terug), `mod`, `inc`, `dec`.
* **Bitwise & Crypto:** `andi`, `xor_vw`, `shftl`, `shftr`, `rol32` (32-bit circulaire rotatie), `rnd32` (32-bit PRNG-mixer bestaande uit `rol32` $\rightarrow$ `xor` $\rightarrow$ `add` $\rightarrow$ `rol32`).
* **Vergelijkingen:** `tst`, `tstz`, `tstn`, `cmpe`, `cmpne`, `cmpgt`, `cmplt`.

---

## 4. Memory Management Unit (MMU) & Geheugenindeling

De centrale `MMU` (`memoryMMU.py`) voorziet alle CPU's op het moederbord van een uniform logisch adresbereik. De standaardindeling omvat **2560 geheugenwoorden** (`0` t/m `2559`):

| Adresbereik (Standaard) | Segment | Toegang | Beschrijving & Hardware-gedrag |
| :--- | :--- | :--- | :--- |
| **`0` – `1023`** | **Program (`Page0`)** | Read-Only | Bevat geassembleerde machinecode. Wordt vooraf geladen via `write_rom()`. Schrijfpogingen veroorzaken een `PermissionError`. |
| **`1024` – `2047`** | **Shared Memory** | Read / Write | Gedeeld werkgeheugen voor alle CPU's. Voorzien van automatische **cyclus-locking**. |
| **`2048` – `2559`** | **Private Memory** | Read / Write | Fysiek gescheiden geheugenpagina's per `cpu_id` (*Lazy Page Allocation*). CPU 0 en CPU 1 lezen/schrijven op hetzelfde logische adres (bijv. `2048`) ieder hun eigen privé-data. |

### Bus-arbitrage & Cyclus-locking (64-woord blokken)
Om geheugenconflicten in **Shared Memory** te voorkomen zonder globale bus-bottlenecks, verdeelt de MMU het gedeelde geheugen in blokken van **64 woorden** (`block_size = 64`):
* Wanneer een CPU naar een adres in blok $B$ schrijft, wordt blok $B$ voor de duur van de huidige klokcyclus geclaimd door die `cpu_id`.
* Als een **andere** CPU binnen dezelfde klokcyclus naar hetzelfde 64-woord blok probeert te schrijven, retourneert de MMU `"STALL"`. De vragende CPU blijft in de `EXECUTE`-fase staan en probeert de schrijfactie in de volgende klokcyclus automatisch opnieuw.
* Aan het einde van elke klokcyclus wist `mmu.tick()` alle blok-locks.

---

## 5. Channel Interface Unit (CIU) & Inter-CPU Bus

Elke Inmos-Z32 CPU beschikt over een on-chip **CIU** die is aangesloten op de gedeelde **`CIUBus`**. De CIU verzorgt zowel taakdistributie als berichtenverkeer tussen CPU's.

### 5.1 Taakdistributie & Cluster-synchronisatie
* **Round-Robin Bus Arbiter (`RCONTEXT`):** Wanneer een CPU een remote context aanvraagt zonder specifiek doel-ID, scant de `CIUBus` alle andere aangesloten CPU's vanaf een roterende hardware-pointer (`rr_pointer`). De eerste CPU die in `WAIT_FOR_WORK` staat én minstens 15 vrije uCores heeft, accepteert de taak.
* **Remote Boot (`RBOOT`):** Stuurt een `CMD_BOOT`-pakket naar een specifieke `target_cpu_id` om diens hoofd-pijplijn te starten op een opgegeven `PC`.
* **Barrier Sync (`ALLSYNC`):** Stuurt een `CMD_SYNC`-broadcast over de bus om te verifiëren of alle andere CPU's geen actieve sub-contexten meer draaien.

### 5.2 Hardware FIFO Mailbox & Flow Control
Elke CIU bevat een inkomende ringbuffer (**FIFO Mailbox**) met een capaciteit van **512 bericht-slots** (`MAILBOX_DEPTH = 512`):
* **Transactie-protocol (Zender):**
  1. `MSG_START`: Reserveert via `CMD_MSG_RESERVE` een slot in de mailbox van de doel-CPU (geeft `TxSlotID` terug). Als de doel-FIFO vol zit, stalt de zendende CPU automatisch in `EXECUTE`.
  2. `MSG_WRITE`: Schrijft één 32-bit woord per keer naar het gereserveerde slot (`CMD_MSG_WRITE_DATA`).
  3. `MSG_DONE`: Markeert het slot als `VALID` (`CMD_MSG_VALIDATE`), waardoor het zichtbaar wordt voor de ontvanger.
* **Ontvangst-protocol (Ontvanger):**
  1. `MSG_PROBE`: Inspecteert non-destructief het slot op `read_pointer` en controleert of `status == "VALID"` en `msg_tag` overeenkomt.
  2. `MSG_OPEN`: Claimt het bericht (`status = "READING"`), schuift `read_pointer` op en geeft een `RxSlotID` terug.
  3. `MSG_READ`: Leest sequentieel de datawoorden uit het bericht.
  4. `MSG_CLOSE`: Geeft het slot weer vrij (`status = "FREE"`) en verlaagt `active_messages`.
* **Hysteresis Flow Control:** Zodra het aantal actieve berichten in een mailbox oploopt tot de **High Watermark (`511` slots)**, blokkeert de CIU nieuwe inkomende reserveringen (`rx_flow_blocked = True`). Pas wanneer de ontvangende CPU berichten heeft verwerkt tot de **Low Watermark (`256` slots)**, wordt de blokkade opgeheven.

---

## 6. I/O-Controller & Randapparatuur

De `IOController` verbindt de CPU via 7 geheugen-geïsoleerde I/O-registers (`reg0` t/m `reg6`) en twee hardware-vlaggen (`write_flag` en `read_flag`) met de randapparatuur.

### 6.1 I/O-Registermap & Handshake-protocol

| Register | Naam | Toegang | Functie |
| :--- | :--- | :--- | :--- |
| **`reg0`** | `DEV` | `OUT` | Doelapparaat: `1` = Character Display, `2` = Graphical Display |
| **`reg1`** | `VAL` | `OUT` | Karaktercode (ASCII) bij Device `1`, of Kleurindex (`0..15`) bij Device `2` |
| **`reg2`** | `X_POS` | `OUT` | X-coördinaat (kolom of pixel-X) |
| **`reg3`** | `Y_POS` | `OUT` | Y-coördinaat (rij of pixel-Y) |
| **`reg4`** | — | — | Gereserveerd |
| **`reg5`** | `CMD` | `OUT` | Instructie-trigger: `1` = Print, `2` = Plot, `3` = Clear, `4` = Move Cursor |
| **`reg6`** | `KBD` | `IN` | Inkomende ASCII-toetscode (`0` indien buffer leeg) |

**Handshake-werking:**
1. Schrijven naar `reg5` via `OUT` zet hardwarematig **`write_flag = 1`**. Zolang `write_flag == 1`, blokkeert elke volgende `OUT`-instructie de CPU (`STALL`).
2. De instructie `IOSYNC` voert een verwerkingsslag uit op de controller: het commando in `reg0..reg5` wordt in de FIFO-cache van het doelapparaat geplaatst en `write_flag` wordt gereset naar `0`. Tegelijkertijd wordt de eerstvolgende toets uit de `kbd_buffer` in `reg6` geplaatst (`read_flag = 1`).
3. Het uitlezen van `reg6` via `IN` reset `read_flag` terug naar `0`.

### 6.2 Randapparatuur Specificaties

#### Graphical Display (`graphDisplay.py`)
* **Resolutie:** **640 × 480 pixels** met hardwarematige clipping (coördinaten buiten `0..639` en `0..479` worden genegeerd).
* **Kleurdiepte:** 16-kleuren Hardware Palette Lookup Table (LUT). Inkomende kleurwaarden worden automatisch gemapt via `color_idx % 16`:
  * `0`: Zwart (`#000000`) | `1..4`: Blauwtinten (Donkerblauw tot Hemelsblauw) | `5..7`: Mint/Groentinten | `8..10`: Geel tot Oranje | `11..14`: Roodtinten | `15`: Helderwit (`#FFFFFF`).
* **Ondersteunde commando's:** `plot` (`CMD = 2`, tekent 1×1 pixel op `(reg2, reg3)` met kleur `reg1`) en `clear` (`CMD = 3`).

#### Character Display (`tekstdisplay.py`)
* **Resolutie:** **80 kolommen × 24 rijen** (VT100-verhouding, groen fosfor-thema `#00ff00` op `#000000`).
* **Besturingstekens & Scrolling:**
  * **ASCII `13` (`\r`):** Voert een gecombineerde **Carriage Return + Line Feed** uit (`cursor_x = 0`, `cursor_y += 1`).
  * **ASCII `10` (`\n`):** Voert een verticale Line Feed uit (`cursor_y += 1`).
  * Bij het bereiken van kolom `80` wrapt de cursor automatisch naar de volgende regel; bij rij `24` schuift het scherm automatisch één regel omhoog (`scroll_screen`).
* **Ondersteunde commando's:** `print` (`CMD = 1`), `clear` (`CMD = 3`) en `move_cursor` (`CMD = 4`, verplaatst cursor naar `(reg2, reg3)` met clamping binnen schermgrenzen).

---

## 7. Instructie-encoding & Machinecodeformaat

Elke instructie in het programmageheugen (`Page0`) wordt gecodeerd als één **decimaal geheel getal** (`MIR`). De decoder ontleedt dit getal met behulp van modulo- en gehele deling (`opcode = MIR % 100`, `payload = MIR // 100`).

| Instructieformaat | Wiskundige Encoding | Omschrijving | Voorbeelden |
| :--- | :--- | :--- | :--- |
| **`ZERO`** | $\text{opcode}$ | Geen operanden | `HALT` (`11`), `IOSYNC` (`12`), `AUTOCLOSE` (`13`), `CLOSE` (`29`) |
| **`ONE_ADDR`** | $\text{addr} \times 100 + \text{opcode}$ | Eén geheugen- of sprongadres | `JMP` (`22`), `JMPT` (`21`), `JMPF` (`20`), `LOCK` (`23`), `UNLOCK` (`24`) |
| **`ONE_REG`** | $R_1 \times 100 + \text{opcode}$ | Eén register ($0 \dots 9$) | `INC` (`80`), `DEC` (`81`), `TSTZ` (`73`), `CPUID` (`96`), `PID` (`94`) |
| **`TWO_REG_REG`** | $(R_2 \times 10 + R_1) \times 100 + \text{opcode}$ | Twee registers ($R_1, R_2 \in 0 \dots 9$) | `LD` (`30`), `ADD` (`50`), `SUB` (`52`), `MUL` (`60`), `TSTE` (`71`), `XOR` (`42`) |
| **`TWO_REG_VAL`** | $(\text{val} \times 10 + R_1) \times 100 + \text{opcode}$ | Doelregister $R_1$ + directe waarde/adres | `LDI` (`31`), `LDM` (`32`), `STO` (`40`), `CONTEXT` (`27`), `RCONTEXT` (`36`), `OUT` (`34`) |

> **Voorbeeld:** De instructie `LDI A, 42` (waarbij `LDI` = `31` en register `A` = `1`) wordt geassembleerd tot:  
> $(42 \times 10 + 1) \times 100 + 31 = 42131$.