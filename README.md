# SternZ32 & ZScripting — Retro Multi-Core Computing

> *"De charme van de Z80, de parallelle kracht van de Inmos Transputer, en een programmeertaal zo toegankelijk als BASIC."*

Welkom bij het **SternZ32 & ZScripting** project! Dit project is een eerbetoon aan het gouden tijdperk van de homecomputers en vroege parallelle architectuur. Het combineert een volledig gesimuleerd **SternZ32** multi-CPU computerplatform (gebaseerd op de **Inmos-Z32** architectuur) met **ZScripting**: een moderne, intuïtieve programmeertaal waarmee je zonder moeite parallelle programma's schrijft.

---

## Het Idee & Retro Gevoel

In de jaren '80 maakten processors zoals de **Zilog Z80** en de **Inmos Transputer** hardware tastbaar en begrijpelijk. Je wist precies waar je geheugen begon, hoe je direct naar het beeldscherm schreef en hoe je met een paar regels BASIC of assembly de volledige machine bestuurde.

**SternZ32** brengt dat directe, transparante hardwaregevoel terug—inclusief een **FrontPanel** met knipperende LED-statussen voor elke rekenkern, een klassiek **80×24 groen fosfor-tekstscherm** en een **640×480 16-kleuren grafisch display**—maar dan opgeschaald naar een modern parallel cluster:

* **SternZ32 Hardware (Inmos-Z32 Architectuur):** Een schaalbaar moederbord met $1$ tot $N$ CPU's, waarbij elke CPU beschikt over **32 asynchrone uCores**, een on-chip **CIU (Channel Interface Unit)** met hardwarematige FIFO-mailboxes, en een gedeelde **MMU** met blok-locking.
* **ZScripting ("As simple as BASIC"):** Geen ingewikkelde boilerplate, linker-scripts of zware abstractielagen. Met directe dataflow (`42 -> A`), heldere blokstructuren (`REPEAT`, `IF`, `MATCH`, `ATOMIC`, `SPAWN`) en ingebouwde mailbox-communicatie (`WRITE` / `READ`) schrijf je massaal parallelle simulaties (zoals Mandelbrot-fractals, Monte Carlo Pi-benaderingen en N-body fysica) net zo eenvoudig als vroeger in BASIC.

--- 

## Projectstructuur & Documentatie

De repository is opgebouwd rond de compiler-toolchain, de hardware-emulator en uitgebreide naslagwerken:

* **[ZScripting Programmeurshandleiding (`ZScripting_Manual.md`)](./ZScripting/zscripting_programmeurshandleiding.md)** — Volledige gids voor de taal, geheugenallocatie (`MAP`), macro's, control-flow, `SPAWN`-pijplijnen, `ATOMIC`-locks en CIU-mailboxes.
* **[SternZ32 Hardware Guide (`SternZ32_Hardware_Guide.md`)](./SternZ32A/sternz32_hardware_guide.md)** — Technische architectuurgids over het moederbord, de 4-fasige CPU-klok, de 32-uCore microcode-matrix, de MMU, de CIU-bus en I/O-randapparatuur.
* `zscript.py` — De ZScripting compiler & assembler (vertaalt `.zs` broncode naar STERN-Z32 assembly of machinecode).
* `SternZ32A.py` — De SternZ32 mainboard-emulator met FrontPanel en grafische randapparatuur.
* `zscripts/` — Voorbeeldprogramma's in ZScripting (o.a. `mandelbrotSLOT.zs`, `mandelbrotNET2.zs`, `montecarlo2.zs`, `N-body-bh2.zs` en `heat20_donutHPx.zs`).

---

## Aan de slag (Quick Start)

Het uitvoeren van een ZScript bestaat uit twee stappen: eerst compileer je het `.zs`-bestand naar binaire machinecode (`firmware.bin`), en vervolgens start je het SternZ32-moederbord met het gewenste aantal CPU's.

### 1. ZScript compileren met `zscript.py`

Compileer een ZScripting-bestand naar machinecode (`--format bin`) om het op de emulator te draaien:

```bash
python zscript.py ./zscripts/mandelbrotSLOT.zs --format bin -o firmware.bin
```

Wil je inspecteren hoe ZScripting wordt vertaald naar low-level STERN-Z32 assembly? Gebruik dan `--format asm`:

```bash
python zscript.py ./zscripts/mandelbrotSLOT.zs --format asm
```

### 2. Het SternZ32 Platform starten met `SternZ32A.py`

Start de emulator met de gecompileerde firmware en geef als tweede argument het **aantal CPU's** mee (bijvoorbeeld `1` of `8`). Voor maximale simulatiesnelheid wordt **PyPy3** aanbevolen:

```bash
# Draai op een enkele CPU (Master CPU 0 met 32 uCores)
pypy3 SternZ32A.py ../ZScripting/firmware.bin 1

# Draai op een parallel cluster van 8 CPU's (8 x 32 = 256 uCores)
pypy3 SternZ32A.py ../ZScripting/firmware.bin 8
```

*(Je kunt `pypy3` ook vervangen door standaard `python` / `python3` als PyPy niet geïnstalleerd is.)*

---

## Voorbeeld: ZScripting in vogelvlucht

Een klein voorproefje van hoe leesbaar en direct ZScripting werkt:

```zscript
MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main
    SHARED counter 1
}

PROGRAM {
main:
    0 -> A
    A -> [counter]          ; Schrijf 0 naar gedeeld geheugen

    10 -> B
    REPEAT I TIMES 5 {
        ADD A, B            ; Tel 10 op bij A (5 keer)
    }

    A -> [counter]          ; Resultaat (50) opslaan in Shared RAM
    HALT
}
```

---

## Vereisten

* **Python 3** (en bij voorkeur **PyPy3** voor hoge kloksnelheden in de simulator)
* **`lark`** (`pip install lark`) — Voor het parsen van de ZScripting-grammatica
* **`tkinter`** — Voor het FrontPanel, het Character Display en het Graphical Display