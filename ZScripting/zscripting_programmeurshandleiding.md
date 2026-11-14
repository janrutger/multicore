# ZScripting Programmeurshandleiding (STERN-Z32 Architectuur)

Welkom bij de officiële programmeurshandleiding voor **ZScripting**, de programmeertaal voor het **STERN-Z32** parallelle computerplatform. ZScripting combineert directe toegang tot de low-level STERN-Z32 assembly-instructieset met krachtige high-level abstracties voor geheugenbeheer, control-flow, hygiënische macro's, multi-context concurrency en inter-CPU communicatie via de CIU (Communication Interface Unit).

---

## Inhoudsopgave
1. [Architectuur & Registers](#1-architectuur--registers)
2. [Programmastructuur & Lexicale Regels](#2-programmastructuur--lexicale-regels)
3. [Het `MAP`-blok: Geheugen, Constanten & I/O](#3-het-map-blok-geheugen-constanten--io)
4. [Macro's & Pre-processor (`MACRO` & `INCLUDE`)](#4-macros--pre-processor-macro--include)
5. [Dataflow & Geheugentoegang (`->`)](#5-dataflow--geheugentoegang--)
6. [Control-Flow Constructies (`IF`, `REPEAT`, `MATCH`)](#6-control-flow-constructies-if-repeat-match)
7. [Parallelle Executie & Synchronisatie (`CONTEXT`, `SPAWN`, `ATOMIC`)](#7-parallelle-executie--synchronisatie-context-spawn-atomic)
8. [CIU Mailbox Communicatie (`WRITE` & `READ`)](#8-ciu-mailbox-communicatie-write--read)
9. [Hardware I/O & Randapparatuur](#9-hardware-io--randapparatuur)
10. [Volledige STERN-Z32 Instructieset Referentie](#10-volledige-stern-z32-instructieset-referentie)

---

## 1. Architectuur & Registers

De STERN-Z32 beschikt over **10 hardware-registers** (32-bit). Register `I` vervult een speciale rol bij geïndexeerde geheugentoegang en bepaalde high-level statements.

| Register | ID | Functie & Bijzonderheden |
| :--- | :---: | :--- |
| **`I`** | `0` | **Index Register.** Wordt door de hardware gebruikt voor geïndexeerde geheugenoperaties (`LDX`, `STX`) en intern gebruikt door `WRITE` en `READ` statements. |
| **`A`** | `1` | Algemeen register / Accumulator |
| **`B`** | `2` | Algemeen register |
| **`C`** | `3` | Algemeen register |
| **`K`** | `4` | Algemeen register |
| **`L`** | `5` | Algemeen register |
| **`M`** | `6` | Algemeen register |
| **`X`** | `7` | Algemeen register |
| **`Y`** | `8` | Algemeen register |
| **`Z`** | `9` | Algemeen register |

> **Let op:** Register- en instructienamen zijn hoofdlettergevoelig en moeten altijd in **HOOFDLETTERS** worden geschreven.

---

## 2. Programmastructuur & Lexicale Regels

Elk ZScripting-bestand (`.zs`) bestaat uit twee verplichte hoofdsecties: het **`MAP`**-blok (declaratie van geheugen, constanten, I/O-poorten en macro's) en het **`PROGRAM`**-blok (de uitvoerbare code).

```zscript
; Dit is een commentaarregel (begint met een puntkomma)

MAP {
    ; Configuratie, geheugenallocatie, constanten en macro's
}

PROGRAM {
    ; Labels, ZScripting statements en STERN-Z32 assembly instructies
}
```

### Lexicale regels
* **Commentaar:** Begint met `;` en loopt tot het einde van de regel.
* **Identifiers & Labels:** Bestaan uit letters, cijfers, underscores (`_`) en koppeltekens (`-`), en moeten beginnen met een letter of underscore (`[a-zA-Z_][a-zA-Z0-9_\-]*`).
* **Labels definiëren:** Eindigen op een dubbele punt (`mijn_label:`).
* **Getallen:** Ondersteunt gehele getallen met of zonder minteken (bijv. `42`, `-1`).

---

## 3. Het `MAP`-blok: Geheugen, Constanten & I/O

In het `MAP`-blok worden alle compile-time definities en geheugenindelingen vastgelegd. De compiler vertaalt alle gedeclareerde symbolen automatisch naar hun berekende geheugenadressen of waarden.

### 3.1 Geheugenindeling (`MEMORY`, `MEMSIZE`, `SP`)
Het geheugen van de STERN-Z32 is opgedeeld in drie segmenten: `PROGRAM` (ROM), `SHARED` (gedeeld RAM) en `PRIVATE` (lokaal RAM).

#### Expliciete geheugenmap (Aanbevolen)
```zscript
MAP {
    MEMORY {
        PROGRAM 1024    ; Programma-geheugen (bijv. adres 0..1023)
        SHARED  1024    ; Gedeeld geheugen (bijv. adres 1024..2047)
        PRIVATE 512     ; Privé geheugen (bijv. adres 2048..2559)
    }
    SP 64               ; Optioneel: reserveer stackruimte bovenaan PRIVATE RAM (standaard 0)
}
```
*(Als `MEMORY` niet expliciet wordt opgegeven, gebruikt de compiler standaard `MEMSIZE 2560` met een verdeling van 1024 / 1024 / 512, of bij een aangepaste `MEMSIZE N` een verdeling van 50% / 25% / 25%.)*

### 3.2 Startpunt (`START`)
Met `START` geef je het startlabel aan waar de executie begint. De compiler plaatst automatisch een bootstrap-vector (`JMP <LABEL>`) aan het begin van de code.
```zscript
START main
```

### 3.3 Geheugenallocatie (`SHARED`, `PRIVATE`, `RES`)
Variabelen en arrays kunnen statisch worden gealloceerd in het geheugen:

* **`SHARED <naam> <grootte>`:** Wijst geheugen toe in **SHARED RAM**. Dit segment groeit **opwaarts** vanaf het begin van het `SHARED`-segment.
* **`PRIVATE <naam> <grootte>`:** Wijst geheugen toe in **PRIVATE RAM**. Dit segment groeit **neerwaarts** vanaf de bovenkant van het `PRIVATE`-segment (onder een eventuele `SP`-stack).
* **`RES <naam> <grootte>`:** Legacy alias voor `PRIVATE`.

```zscript
SHARED cur_pixel 1          ; 1 word in Shared RAM
SHARED grid_current 400     ; Array van 400 words in Shared RAM
PRIVATE SEED 1              ; 1 word in Private RAM
```

### 3.4 Constanten & I/O-aliassen (`CONST` & `IO`)
* **`CONST <naam> <waarde>`:** Definieert een compile-time constante.
* **`IO <naam> <poortnummer>`:** Definieert een leesbare naam voor een hardware I/O-poort.

```zscript
CONST MAX_ITER 32
CONST BAILOUT 4000

IO DEV 0
IO VAL 1
IO CMD 5
```

---

## 4. Macro's & Pre-processor (`MACRO` & `INCLUDE`)

ZScripting ondersteunt parametrische, **hygiënische macro's**. Dit betekent dat labels binnen een macro bij elke aanroep automatisch een uniek voorvoegsel krijgen (`__M<id>_`), zodat je macro's met loops of sprongen probleemloos meerdere keren kunt aanroepen zonder label-conflicten.

### 4.1 Macro's definiëren en aanroepen
Macro's worden gedefinieerd in het `MAP`-blok en aangeroepen in het `PROGRAM`-blok (of vanuit andere macro's).

```zscript
MAP {
    MACRO fmul_round(Rx, Ry, scale_val, half_val) {
        MUL Rx, Ry
        ADDI Rx, half_val
        DIVI Rx, scale_val
    }

    MACRO waitMatrix() {
        _waitMatrix:
            ALLSYNC _waitMatrix
    }
}

PROGRAM {
main:
    fmul_round(A, L, 1000, 500)
    waitMatrix()
}
```
> **Slimme type-correctie in macro's:** Als je binnen een macro `LD Rx, param` gebruikt en je geeft bij de aanroep een getal of `CONST` mee als `param`, zet de compiler `LD` automatisch om naar `LDI`.

### 4.2 Standaardbibliotheek importeren (`INCLUDE`)
Met het pre-processor keyword `INCLUDE` in het `MAP`-blok importeer je voorgedefinieerde macro's uit de standaardbibliotheek (`std_macros.zs`). Meerdere macro's kunnen kommagescheiden worden opgegeven:

```zscript
MAP {
    INCLUDE startTask, rand, fmul_round
}
```

**Beschikbare macro's in `std_macros.zs`:**
* `startTask(task, arg)`: Probeert een context eerst remote te starten via `RCONTEXT` en valt terug op lokaal via `CONTEXT` tot er een uCore beschikbaar is.
* `rand(val, size)`: Genereert een pseudo-random getal in register `val` op basis van `PRIVATE SEED 1` en verschuift dit `size` bits naar rechts (`SHIFTR`).
* `waitMatrix()`: Voert een cluster-brede barrier-synchronisatie (`ALLSYNC`) uit.
* `fmul_round(Rx, Ry, scale, half)`: Fixed-point vermenigvuldiging met round-to-nearest afronding.

---

## 5. Dataflow & Geheugentoegang (`->`)

In plaats van aparte load- en store-mnemonics te schrijven, biedt ZScripting een intuïtieve dataflow-operator (`bron -> doel`). De compiler vertaalt dit automatisch naar de juiste STERN-Z32 instructies (`LDI`, `LD`, `LDM`, `STO`, `LDX`, `STX`).

| ZScripting Syntax | Betekenis | Gegenereerde Assembly |
| :--- | :--- | :--- |
| `42 -> A` | Laad constante / immediate in register `A` | `LDI A, 42` |
| `MAX_ITER -> B` | Laad `CONST`-waarde in register `B` | `LDI B, MAX_ITER` |
| `A -> B` | Kopieer register `A` naar register `B` | `LD B, A` |
| `[cur_pixel] -> A` | Lees directe geheugenlocatie in register `A` | `LDM A, cur_pixel` |
| `A -> [cur_pixel]` | Schrijf register `A` naar directe geheugenlocatie | `STO A, cur_pixel` |
| `[1024] -> A` | Lees direct geheugenadres `1024` in register `A` | `LDM A, 1024` |
| `[grid + X] -> A` | Lees geïndexeerd geheugen (`grid + X`) in `A` | `LD I, X` *(indien $\neq$ I)* + `LDX A, grid` |
| `A -> [grid + X]` | Schrijf register `A` naar geïndexeerd geheugen | `LD I, X` *(indien $\neq$ I)* + `STX A, grid` |

> **Belangrijk bij geïndexeerde toegang (`[basis + Reg]`):** De hardware ondersteunt alleen register `I` als indexregister. Als je een ander register opgeeft (zoals `[grid + X]`), genereert de compiler automatisch eerst `LD I, X` en overschrijft daarbij de huidige waarde in `I`!

---

## 6. Control-Flow Constructies (`IF`, `REPEAT`, `MATCH`)

### 6.1 Condities
In ZScripting worden condities geschreven met exact twee operanden en ondersteunen uitsluitend de volgende vergelijkingen:
* `(Rx == Ry)` — Gelijk aan (`TSTE`)
* `(Rx > Ry)` — Groter dan (`TSTG`)
* `(Rx ZERO)` — Is register gelijk aan 0 (`TSTZ`) *(alleen geldig in `IF`, `MATCH` en `SPAWN`)*

*(Opmerking: De linker- en rechterzijde van `==` en `>` moeten registers zijn, of een register en een symbool/constante afhankelijk van de onderliggende hardware-test. In de praktijk worden constanten eerst in een register geladen.)*

### 6.2 `IF ... ELSE` Statement
Een `IF`-statement vereist expliciet de evaluatiemodus **`TRUE`** (voer blok uit als conditie waar is) of **`FALSE`** (voer blok uit als conditie onwaar is). Een `ELSE`-tak is optioneel.

```zscript
IF (A == B) TRUE {
    0 -> C
} ELSE {
    1 -> C
}

IF (A ZERO) FALSE {
    ; Wordt uitgevoerd zolang A ongelijk is aan 0
    DEC A
}
```

### 6.3 `REPEAT` Lussen
ZScripting kent drie varianten van de `REPEAT`-lus:

1. **Vast aantal iteraties (`TIMES`):** Laadt de teller in het opgegeven register en telt af tot 0.
   ```zscript
   REPEAT I TIMES 10 {
       0 -> [array + I]
   }
   ```
2. **Conditionele lus (`UNTIL`):** Herhaalt het blok totdat aan de voorwaarde (`==` of `>`) wordt voldaan (post-test loop).
   ```zscript
   0 -> X
   10 -> M
   REPEAT UNTIL (X == M) {
       INC X
   }
   ```
3. **Gecombineerde lus (`TIMES ... UNTIL`):** Stopt zodra het aantal iteraties op is **óf** zodra de `UNTIL`-conditie waar wordt.
   ```zscript
   REPEAT K TIMES 100 UNTIL (A > B) {
       ; Lus-body
   }
   ```

### 6.4 `MATCH` Statement
Met `MATCH` kun je meerdere waarden of conditionele guards overzichtelijk afhandelen, vergelijkbaar met een `switch`- of `match`-expressie. Elke arm eindigt na uitvoering automatisch het `MATCH`-blok (geen fall-through).

```zscript
MATCH A {
    0 -> {
        ; Uitgevoerd als A == 0 (via TST A, 0)
    }
    1 -> {
        ; Uitgevoerd als A == 1
    }
    (A > B) TRUE -> {
        ; Conditionele guard: uitgevoerd als A > B
    }
    (C ZERO) FALSE -> {
        ; Conditionele guard: uitgevoerd als C != 0
    }
    DEFAULT -> {
        ; Fallback als geen enkele arm overeenkwam
    }
}
```
*(Je kunt `MATCH` ook zonder target-variabele gebruiken — `MATCH { ... }` — als je uitsluitend met conditionele guards en `DEFAULT` werkt.)*

---

## 7. Parallelle Executie & Synchronisatie (`CONTEXT`, `SPAWN`, `ATOMIC`)

De STERN-Z32 is ontworpen voor massaal parallelle executie over lokale **uCores** en externe CPU's in het netwerk.

### 7.1 Contexts & Remote Execution
* **`CONTEXT Rx, label`:** Start lokaal een nieuwe parallelle uCore-context vanaf `label`. De waarde in register `Rx` van de aanroepende thread wordt gekopieerd naar **hetzelfde register `Rx`** in de nieuwe context. Zet de hardware-statusvlag op succes of falen (als alle lokale context-slots vol zijn), te testen met `SUCCES` of `FAIL`.
* **`RCONTEXT Rx, label`:** Identiek aan `CONTEXT`, maar injecteert de taak op een beschikbare remote CPU via het CIU-netwerk.
* **`RBOOT Rx, label`:** Boot een specifieke externe CPU (waarvan het CPU-ID in `Rx` staat) en laat deze starten op `label`.
* **`CLOSE` / `AUTOCLOSE`:** Beëindigt een worker-context. `CLOSE` behoudt het resultaat in het startregister zodat een ouder-thread dit kan ophalen met `JOIN Rx, retry_label`. `AUTOCLOSE` geeft de uCore direct terug aan de vrije pool (gebruikt voor fire-and-forget workers).
* **`SUSPEND`:** Pauzeert de huidige CPU/context.
* **`SYNC label` / `ALLSYNC label`:** Wacht totdat alle lokale contexten (`SYNC`) of alle contexten in het gehele CPU-cluster (`ALLSYNC`) zijn afgerond. Springt terug naar `label` zolang er nog actieve workers zijn.

### 7.2 `SPAWN` Pijplijn
Het `SPAWN`-statement genereert een complete, hoog-performante producer-consumer pijplijn voor het parallel verwerken van een reeks taken, inclusief automatische terugval bij een volle matrix en een waterdichte drain-fase aan het einde.

```zscript
SPAWN WORKER_LABEL A UNTIL (I == MAX) TRUE UPDATE {
    INC I
} HARVEST B {
    ADD X, B
}
```
**Werking van `SPAWN`:**
1. Test de stopconditie `UNTIL (<conditie>) <TRUE|FALSE>`. Als deze bereikt is, springt de pijplijn naar de drain-fase.
2. Roept `CONTEXT <input_reg>, <worker_label>` aan.
3. Bij succes wordt het `UPDATE`-blok uitgevoerd en probeert de CPU direct via `JOIN <harvest_reg>` eventuele voltooide resultaten te oogsten en het `HARVEST`-blok uit te voeren.
4. Als de matrix vol is (`FAIL`), oogst de CPU eerst afgeronde workers via `JOIN` en voert het `HARVEST`-blok uit voordat hij opnieuw probeert te spawnen.
5. Zodra alle taken zijn uitgestuurd, wacht de drain-fase met `JOIN` en `SYNC` tot alle lopende workers zijn geoogst.

### 7.3 `ATOMIC` Kritieke Secties
Wanneer meerdere parallelle workers tegelijkertijd gedeelde data in `SHARED` RAM aanpassen, voorkomt het `ATOMIC`-statement race conditions door middel van een hardware spin-lock (`LOCK` / `UNLOCK`) op een mutex-adres.

```zscript
MAP {
    SHARED MUTEX_LOCK 1
    SHARED SHARED_COUNTER 1
}

PROGRAM {
worker:
    ATOMIC MUTEX_LOCK {
        [SHARED_COUNTER] -> K
        INC K
        K -> [SHARED_COUNTER]
    }
    AUTOCLOSE
}
```

---

## 8. CIU Mailbox Communicatie (`WRITE` & `READ`)

CPU's en contexten kunnen asynchroon berichten met elkaar uitwisselen via de hardwarematige **CIU Mailbox API**. Een bericht bestaat uit een numerieke **TAG** (in een register) en nul of meer 32-bit payload-woorden.

### 8.1 Berichten versturen (`WRITE`)
```zscript
100 -> B                ; B bevat de bericht-TAG (bijv. 100)
WRITE B (A, X, Y)       ; Verstuur bericht met TAG 100 en 3 payload-waarden (A, X, Y)
WRITE B ()              ; Verstuur een signaalbericht zonder payload
```
*(Expandeert naar `LDI I, <aantal>`, `MSG_START`, `MSG_WRITE` per argument en `MSG_DONE`. Overschrijft register `I`.)*

### 8.2 Berichten ontvangen (`READ`)
`READ` controleert non-blocking (`MSG_PROBE`) of er een bericht met de opgegeven TAG klaarstaat. Zo ja, dan wordt het bericht geopend, worden de waarden uitgelezen in de opgegeven registers, wordt het mailbox-slot gesloten en wordt het codeblok uitgevoerd. Staat er geen bericht klaar, dan wordt het blok overgeslagen.

```zscript
100 -> B                ; Zoek naar bericht met TAG 100
READ B (A, X, Y) {
    ; Dit blok wordt alleen uitgevoerd als er een bericht was.
    ; A, X en Y bevatten nu de ontvangen payload.
}
```
*(Expandeert naar `MSG_PROBE`, `FAIL`, `MSG_OPEN I`, `MSG_READ`, `MSG_CLOSE I` gevolgd door het codeblok. Overschrijft register `I`.)*

---

## 9. Hardware I/O & Randapparatuur

Communicatie met randapparatuur verloopt via de instructies `OUT Rx, <poort>` en `IN Rx, <poort>`, gevolgd door `IOSYNC` om de I/O-controller een kloktik te geven.

### Overzicht I/O-poorten
| Poort | Richting | Functie | Waarden / Betekenis |
| :---: | :---: | :--- | :--- |
| **`0`** | `OUT` | **Device Select (`DEV`)** | `1` = Character Display, `2` = Graphical Display |
| **`1`** | `OUT` | **Value / Kleur (`VAL`)** | ASCII-waarde (bij Device `1`) of Kleurcode (bij Device `2`) |
| **`2`** | `OUT` | **X-coördinaat (`X_POS`)** | Horizontale pixelpositie (`0..639`) |
| **`3`** | `OUT` | **Y-coördinaat (`Y_POS`)** | Verticale pixelpositie (`0..479`) |
| **`5`** | `OUT` | **Command Trigger (`CMD`)** | `1` = Print karakter, `2` = Plot pixel, `3` = Clear screen |
| **`6`** | `IN` | **Keyboard Input (`KBD`)** | Geeft ASCII-code van ingedrukte toets terug (`0` indien geen toets) |

### Voorbeeld: Pixel tekenen op het Graphical Display
```zscript
2 -> A
OUT A 0         ; Selecteer Graphical Display (Device 2)
12 -> A
OUT A 1         ; Kies kleur 12
100 -> A
OUT A 2         ; X = 100
150 -> A
OUT A 3         ; Y = 150
2 -> A
OUT A 5         ; Voer commando 2 uit (Plot pixel)
IOSYNC          ; Synchroniseer I/O-controller
```

---

## 10. Volledige STERN-Z32 Instructieset Referentie

Alle onderstaande mnemonics kunnen rechtstreeks in het `PROGRAM`-blok en binnen `MACRO`'s worden gebruikt.

### Geheugen & Data-overdracht
| Instructie | Operanden | Beschrijving |
| :--- | :--- | :--- |
| `LDI` | `Rx, val` | Laad directe integerwaarde (`val`) in register `Rx` |
| `LD` | `Rx, Ry` | Kopieer waarde van register `Ry` naar register `Rx` |
| `LDM` | `Rx, addr` | Laad waarde uit geheugenadres `addr` in register `Rx` |
| `STO` | `Rx, addr` | Sla waarde van register `Rx` op in geheugenadres `addr` |
| `LDX` | `Rx, addr` | Laad waarde uit geïndexeerd adres `(addr + I)` in `Rx` |
| `STX` | `Rx, addr` | Sla waarde van `Rx` op in geïndexeerd adres `(addr + I)` |

### Rekenkundige & Bitwise Bewerkingen
| Instructie | Operanden | Beschrijving |
| :--- | :--- | :--- |
| `ADD` / `ADDI` | `Rx, Ry` / `Rx, val` | Tel `Ry` of `val` op bij `Rx` (`Rx = Rx + ...`) |
| `SUB` / `SUBI` | `Rx, Ry` / `Rx, val` | Trek `Ry` of `val` af van `Rx` (`Rx = Rx - ...`) |
| `MUL` / `MULI` | `Rx, Ry` / `Rx, val` | Vermenigvuldig `Rx` met `Ry` of `val` |
| `DIV` / `DIVI` | `Rx, Ry` / `Rx, val` | Gehele deling van `Rx` door `Ry` of `val` |
| `MOD` | `Rx, Ry` | Modulo: `Rx = Rx % Ry` |
| `INC` / `DEC` | `Rx` | Verhoog (`Rx + 1`) of verlaag (`Rx - 1`) register `Rx` |
| `XOR` | `Rx, Ry` | Bitwise XOR: `Rx = Rx ^ Ry` |
| `ANDI` | `Rx, val` | Bitwise AND met immediate: `Rx = Rx & val` |
| `SHIFTL` | `Rx, val` | Bitwise shift naar links met `val` posities |
| `SHIFTR` | `Rx, val` | Bitwise shift naar rechts met `val` posities |
| `RND32` | `Rx, val` | 32-bit pseudo-random mixer op state `Rx` met constante `val` |

### Vergelijkingen & Sprongen (Branching)
| Instructie | Operanden | Beschrijving |
| :--- | :--- | :--- |
| `TST` | `Rx, val` | Test of `Rx == val` (zet statusvlag) |
| `TSTE` | `Rx, Ry` | Test of `Rx == Ry` (zet statusvlag) |
| `TSTG` | `Rx, Ry` | Test of `Rx > Ry` (zet statusvlag) |
| `TSTZ` | `Rx` | Test of `Rx == 0` (zet statusvlag) |
| `JMP` | `label` | Onvoorwaardelijke sprong naar `label` |
| `JMPT` | `label` | Spring naar `label` als de vorige test **WAAR** was |
| `JMPF` | `label` | Spring naar `label` als de vorige test **ONWAAR** was |
| `SUCCES` | `label` | Spring naar `label` als de vorige operatie (`CONTEXT`, `LOCK`, etc.) slaagde |
| `FAIL` | `label` | Spring naar `label` als de vorige operatie (`CONTEXT`, `MSG_PROBE`, etc.) faalde |

### Concurrency, Systeem & Hardware I/O
| Instructie | Operanden | Beschrijving |
| :--- | :--- | :--- |
| `CONTEXT` | `Rx, label` | Start lokale uCore op `label` en geef `Rx` mee |
| `RCONTEXT` | `Rx, label` | Start remote uCore via CIU op `label` en geef `Rx` mee |
| `RBOOT` | `Rx, label` | Start remote CPU met ID `Rx` op `label` |
| `JOIN` | `Rx, label` | Oogst resultaat in `Rx` als context klaar is; spring anders naar `label` |
| `CLOSE` | — | Sluit context af en behoud resultaat in startregister voor `JOIN` |
| `AUTOCLOSE` | — | Sluit context af en geef uCore direct vrij |
| `SYNC` | `label` | Spring naar `label` zolang er nog lokale contexten actief zijn |
| `ALLSYNC` | `label` | Spring naar `label` zolang er nog contexten in het cluster actief zijn |
| `LOCK` | `addr` | Atomaire test-and-set op mutex-adres `addr` (zet `SUCCES` bij winst) |
| `UNLOCK` | `addr` | Geeft mutex-adres `addr` weer vrij |
| `CPUID` | `Rx` | Laadt het ID van de huidige CPU in `Rx` |
| `PID` | `Rx` | Laadt het proces-/context-ID in `Rx` |
| `OUT` | `Rx, port` | Schrijft register `Rx` naar I/O-poort `port` |
| `IN` | `Rx, port` | Leest I/O-poort `port` naar register `Rx` |
| `IOSYNC` | — | Geeft een kloktik aan de I/O-controller |
| `SUSPEND` | — | Pauzeert de huidige CPU |
| `HALT` | — | Stopt de executie volledig |

### Low-level CIU Mailbox Instructies
*(Worden doorgaans gegenereerd door `WRITE` en `READ`, maar zijn ook direct aanroepbaar)*

| Instructie | Operanden | Beschrijving |
| :--- | :--- | :--- |
| `MSG_START` | `Rx, Ry` | Start uitgaand bericht met tag `Rx` en grootte `Ry`; `Ry` ontvangt `TxSlotID` |
| `MSG_WRITE` | `Ry, Rx` | Schrijft waarde `Rx` naar mailbox-slot `Ry` |
| `MSG_DONE` | `Ry` | Markeert uitgaand bericht in slot `Ry` als verzendklaar |
| `MSG_PROBE` | `Rx` | Controleert of er een bericht met tag `Rx` klaarstaat (zet `SUCCES`/`FAIL`) |
| `MSG_OPEN` | `Rx` | Claimt het gevonden bericht en plaatst het `RxSlotID` in `Rx` |
| `MSG_READ` | `Ry, Rx` | Leest het volgende payload-woord uit slot `Ry` in register `Rx` |
| `MSG_CLOSE` | `Ry` | Sluit het inkomende mailbox-slot `Ry` en geeft het vrij |