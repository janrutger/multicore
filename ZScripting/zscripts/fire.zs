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
    CONST MAX_HEAT 15

    ; Gedeeld warmteraster in Shared RAM (1024 locaties)
    SHARED heat_grid 1024

    ; PRNG macro voor willekeurige afkoeling en vuurflikkering
    PRIVATE SEED 1
    MACRO rand(val, size) {
        LDM val SEED
        RND32 val 21
        STO val SEED
        SHIFTR val size
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

    ; 1. Initialiseer GraphicalDisplay bus op CPU0
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
        LDI B, 32
        MUL A, B
        ADD A, X
        
        LDI B, 15
        B -> [heat_grid + A]   ; Bodem vol hitte
        INC X
    }

    ; 4. Lanceer Worker cores voor parallelle kolommen in Shared RAM
    LDI A, 0
    RCONTEXT A WORKER_COL_1

    LDI A, 11
    RCONTEXT A WORKER_COL_2

    LDI A, 22
    RCONTEXT A WORKER_COL_3

MASTER_DISPLAY_LOOP:
    ; CPU0 houdt de bodembron (Y=31) levend met flikkeringen
    31 -> Y
    0 -> X
    GRID_W -> Z
    REPEAT UNTIL (X == Z) {
        rand(A, 28)
        LDI B, 4
        MOD A, B                ; A = 0..3
        LDI B, 15
        SUB B, A                ; Hitte tussen 12 en 15
        
        Y -> A
        LDI C, 32
        MUL A, C
        ADD A, X

        B -> [heat_grid + A]
        INC X
    }

    ; CPU0 leest het raster uit Shared RAM en tekent het op het scherm
    30 -> Y                     ; Start bij Y = 30 omhoog naar Y = 0
MASTER_ROW_LOOP:
    0 -> X                      ; X van 0 tot 31
MASTER_COL_LOOP:
    ; Bereken adres in Shared RAM: (Y * 32) + X
    Y -> A
    LDI Z, 32
    MUL A, Z
    ADD A, X                    ; A = index
    
    [heat_grid + A] -> B        ; Lees hitte uit Shared RAM
    
    ; Stuur plot-commando naar GraphicalDisplay met 15x15 pixels schaling
    B -> A                      ; Kleur-index
    OUT A VAL

    X -> A
    MULI A 5                   ; Schaal X naar fysieke pixels
    OUT A X_POS

    Y -> A
    MULI A 5                   ; Schaal Y naar fysieke pixels
    OUT A Y_POS

    PLOT_CMD -> A
    OUT A CMD
    IOSYNC

    INC X
    32 -> Z
    IF (X == Z) FALSE {
        JMP MASTER_COL_LOOP
    }

    ; Check of we op rij 0 waren (laatste rij van het frame)
    0 -> Z
    IF (Y == Z) TRUE {
        JMP MASTER_DISPLAY_LOOP ; Frame compleet, opnieuw beginnen
    }

    DEC Y
    JMP MASTER_ROW_LOOP


; ==========================================================
; WORKER CONTEXTEN (Pure rekenkracht in Shared RAM, 0 I/O)
; ==========================================================
WORKER_COL_1:
    0 -> K                      ; Start X (0)
    10 -> L                     ; Eind X (10)
    JMP FIRE_WORKER_ENTRY

WORKER_COL_2:
    11 -> K                     ; Start X (11)
    21 -> L                     ; Eind X (21)
    JMP FIRE_WORKER_ENTRY

WORKER_COL_3:
    22 -> K                     ; Start X (22)
    31 -> L                     ; Eind X (31)
    JMP FIRE_WORKER_ENTRY

FIRE_WORKER_ENTRY:
    0 -> I
    0 -> A
    0 -> B
    0 -> C
    0 -> X
    0 -> Y
    0 -> Z

FIRE_TICK_LOOP:
    30 -> Y                     ; Start bij Y = 30 omhoog tot Y = 0

ROW_LOOP:
    K -> X                      ; Zet X op startkolom van deze worker

COL_LOOP:
    ; 1. Bereken adres cel eronder: ((Y + 1) * 32) + X
    Y -> A
    INC A
    LDI B, 32
    MUL A, B
    ADD A, X                    ; A = index cel eronder
    
    [heat_grid + A] -> B        ; Lees hitte eronder uit Shared RAM

    ; 2. Genereer random cooling (0, 1 of 2)
    rand(C, 28)
    LDI Z, 3
    MOD C, Z                    ; C = 0, 1 of 2
    
    IF (B > C) TRUE {
        SUB B, C                ; B = B - C
    }
    IF (B > C) FALSE {
        0 -> B                  ; Clamp op 0
    }

    ; 3. Schrijf nieuwe hitte naar huidige cel in Shared RAM: (Y * 32) + X
    Y -> A
    LDI Z, 32
    MUL A, Z
    ADD A, X                    ; A = index huidige cel
    B -> [heat_grid + A]        ; Shared RAM update

    ; Volgende kolom in range van deze worker
    INC X
    L -> Z
    INC Z                       ; Inclusief eindkolom L
    IF (X == Z) FALSE {
        JMP COL_LOOP
    }

    ; Check of we rij 0 hebben gehad
    0 -> Z
    IF (Y == Z) TRUE {
        JMP FIRE_TICK_LOOP      ; Frame afgerond, opnieuw beginnen bij Y = 30
    }

    DEC Y
    JMP ROW_LOOP
}