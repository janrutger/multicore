MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === I/O POORTEN VOOR GRAPHICAL DISPLAY ===
    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2
    CONST CLR_CMD 3

    CONST GRID_W 32
    CONST GRID_H 32
    CONST TOTAL_FRAMES 50       ; Aantal te verwerken simulatie-frames

    ; Gedeeld warmteraster in Shared RAM (1024 locaties: adres 1024 t/m 2047)
    SHARED heat_grid 1024

    ; PRNG macro voor willekeurige afkoeling en vuurflikkering
    PRIVATE SEED 1
    MACRO rand(val, size) {
        LDM val SEED
        RND32 val 21
        STO val SEED
        SHIFTR val size
    }

    ; === DYNAMISCHE NETWERK TASK DISPATCHER (CIU & Lokaal) ===
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task   ; 1. Injecteer remote worker via CIU netwerk
            SUCCES _spawnd
            CONTEXT arg task    ; 2. Fallback lokaal op CPU 0 als netwerk vol zit
            SUCCES _spawnd
            JMP _spawntask      ; Wacht tot er een uCore vrijkomt
        _spawnd:
    }

    ; === BARRIER SYNCHRONISATIE MACRO ===
    MACRO waitMatrix() {
        _waitMatrix:
        ALLSYNC _waitMatrix
    }
}

PROGRAM {

main:
    0 -> I
    0 -> A
    0 -> B
    0 -> C
    0 -> K
    0 -> L
    0 -> M
    0 -> X
    0 -> Y
    0 -> Z

    ; 1. Initialiseer GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Wis het scherm
    CLR_CMD -> A
    OUT A CMD
    IOSYNC

    ; 3. Initialiseer de onderste rij (Y = 31) als vuurbron met maximale hitte
    31 -> Y
    0 -> X
    GRID_W -> Z
    REPEAT UNTIL (X == Z) {
        Y -> A
        MULI A 32
        ADD A X                 ; A = (31 * 32) + X
        
        LDI B 15
        B -> [heat_grid + A]    ; Bodem vol hitte (waarde 15)
        INC X
    }

    TOTAL_FRAMES -> L           ; Frame-teller in L

FRAME_LOOP:
    ; --- STAP A: Vuurbron onderaan (Y = 31) voorzien van willekeurige flikkeringen ---
    31 -> Y
    0 -> X
    GRID_W -> Z
    REPEAT UNTIL (X == Z) {
        rand(A, 28)
        LDI B 4
        MOD A B                 ; A = 0..3
        LDI B 15
        SUB B A                 ; Hitte schommelt tussen 12 en 15
        
        Y -> C
        MULI C 32
        ADD C X

        B -> [heat_grid + C]
        INC X
    }

    ; --- STAP B: Per-kolom RCONTEXT dispatching (X = 0 t/m 31) ---
    0 -> X
    GRID_W -> Z                 ; Z = 32 kolommen
_COL_LOOP:
    startTask(FIRE_SINGLE_COL_WORKER, X)
    INC X
    IF (X == Z) FALSE {
        JMP _COL_LOOP
    }

    ; --- STAP C: Wacht totdat alle 32 kolom-workers klaar zijn ---
    waitMatrix()

    ; --- STAP D: CPU 0 leest Shared RAM uit en tekent het raster (15x15 pixels) ---
    30 -> Y                     ; Start bij Y = 30 omhoog tot Y = 0
MASTER_ROW_LOOP:
    0 -> X                      ; X van 0 tot 31
MASTER_COL_LOOP:
    Y -> A
    MULI A 32
    ADD A X                     ; A = index in Shared RAM (Y * 32 + X)
    
    [heat_grid + A] -> B        ; Lees berekende hitte uit Shared RAM
    
    ; Teken-filter: stuur alleen I/O commando's als er hitte aanwezig is
    ; IF (B ZERO) FALSE {
        B -> A                  ; Kleur-index (0..15)
        OUT A VAL

        X -> A
        MULI A 5               ; Schaal X naar 480px breedte (15x15 blokken)
        OUT A X_POS

        Y -> A
        MULI A 5               ; Schaal Y naar 480px hoogte (15x15 blokken)
        OUT A Y_POS

        PLOT_CMD -> A
        OUT A CMD
        IOSYNC
    ; }

    INC X
    GRID_W -> Z
    IF (X == Z) FALSE {
        JMP MASTER_COL_LOOP
    }

    0 -> Z
    IF (Y == Z) TRUE {
        JMP CHECK_FRAME_COUNT
    }

    DEC Y
    JMP MASTER_ROW_LOOP

CHECK_FRAME_COUNT:
    DEC L
    TSTZ L
    JMPF FRAME_LOOP             ; Herhaal tot alle frames verwerkt zijn

    waitMatrix()
    HALT


; ==========================================================
; WORKER CONTEXT: Berekent exact één kolom X (van Y=30 naar Y=0)
; Register X bevat automatisch de unieke kolom-index (0 t/m 31)
; ==========================================================
FIRE_SINGLE_COL_WORKER:
    0 -> I
    0 -> A
    0 -> B
    0 -> C
    0 -> Y
    0 -> Z

    ; Gebruik de unieke kolom X (meegegeven via RCONTEXT arg) als seed-offset!
    LDM C SEED
    ADD C X                     ; Meng kolom-index X door de seed
    STO C SEED

    30 -> Y                     ; Start bij rij Y = 30 en werk omhoog naar Y = 0

ROW_STEP:
    ; 1. Bereken adres cel eronder: ((Y + 1) * 32) + X
    Y -> A
    INC A
    MULI A 32
    ADD A X                     ; A = index cel eronder (nog ongewijzigd in dit frame)

    [heat_grid + A] -> B        ; Lees warmte uit Shared RAM

    ; 2. Willekeurige afkoeling (0, 1 of 2)
    rand(C, 28)
    LDI Z 3
    MOD C Z

    IF (B > C) TRUE {
        SUB B C
    } ELSE {
    ; IF (B > C) FALSE {
        0 -> B                  ; Clamp op 0
    }

    ; 3. Schrijf nieuwe hitte weg op huidige cel: (Y * 32) + X
    Y -> A
    MULI A 32
    ADD A X
    B -> [heat_grid + A]        ; Directe update in Shared RAM

    ; 4. Controleer of we bovenin (rij 0) zijn aangekomen
    0 -> Z
    IF (Y == Z) TRUE {
        AUTOCLOSE               ; Geef uCore vrij en stuur FINISH signaal
    }

    DEC Y                       ; Increment/Decrement richting top: tel af naar 0!
    JMP ROW_STEP
}

