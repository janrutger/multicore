MAP {
    MEMSIZE 1024
    START main

    RES grid_current 400    ; Huidige temperatuur-raster (20x20 = 400 cellen)
    RES grid_next 400       ; Buffer voor de berekende volgende stap

    CONST ROW_SIZE 20       ; Aantal kolommen/rijen in het raster
    CONST GRID_SIZE 399     ; Laatste cel-index (400 cellen: 0 t/m 399)
    CONST LAST_COL 19       ; Rechterrand kolom-index (ROW_SIZE - 1)
    CONST BOTTOM_START 380  ; Start-index van de onderrand (19 * ROW_SIZE)
    CONST HEAT_SOURCE 355   ; Permanente warmtebron op cel (10, 10) 210

    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2
}

PROGRAM {
main:
    ; --- 1. INITIALISATIE VAN HET RASTER ---
    1 -> A
    0 -> I
    0 -> B
    0 -> M
    0 -> X
    0 -> Y 

    REPEAT I TIMES GRID_SIZE {
        A -> [grid_current + I]
        A -> [grid_next + I]
    }

    ; Permanente warmtebron (temperatuur 70) op cel HEAT_SOURCE (210)
    70 -> A
    HEAT_SOURCE -> I
    A -> [grid_current + I]

    ; ==========================================================
    ;  HOOFD SIMULATIE LUS (Draait 30 diffusie-stappen)
    ; ==========================================================
    20 -> Y                 ; Y telt de simulatierondes (iteraties) 75
SIMULATIE_STAP:
    0 -> X                 ; Start-index X bij cel 0 voor de SPAWN pijplijn
    GRID_SIZE -> B

    ; --- 2. PARALLELLE REKEN-FASE (32 uCores Matrix) ---
    ; SPAWN HEAT_WORKER X UNTIL (X == B) TRUE UPDATE {
    ;     INC X
    ; } HARVEST A {
    ;     ; Enkel uCore vrijmaken; resultaat staat al decentraal in grid_next
    ; }

    REPEAT UNTIL (X == B) {
        spawn:
            CONTEXT X HEAT_WORKER
            FAIL spawn
        INC X    
    }
    ; VERPLICHT: Wacht tot alle 400 gespawnde workers via AUTOCLOSE klaar zijn
    ; voordat de Master-CPU het geheugen gaat uitlezen om het scherm te tekenen!
    WAIT_MATRIX:
        SYNC WAIT_MATRIX

    ; --- 3. SWAP BUFFERS (Kopieer grid_next naar grid_current) ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_next + I] -> A
        A -> [grid_current + I]
    }

    ; --- 4. SERIËLE IN-ORDER DISPLAY-FASE (Master CPU) ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_current + I] -> C

        ; SLIMME I/O FILTER: Verstuur ALLEEN als de temperatuur > 0 is!
        IF (C ZERO) FALSE {
            GRAPH_DEV -> A
            PLOT_CMD  -> B

            OUT A DEV
            DIVI C 5              ; Schaal temperatuur naar kleurpalet
            OUT C VAL             ; Kleurcode op basis van temperatuur

            ; Scherm X-coördinaat: (I % ROW_SIZE) * 10 pixels
            I -> M
            ROW_SIZE -> A
            MOD M A
            MULI M 5
            OUT M X_POS

            ; Scherm Y-coördinaat: (I / ROW_SIZE) * 10 pixels
            I -> M
            DIVI M ROW_SIZE
            MULI M 5
            OUT M Y_POS

            OUT B CMD             ; Trigger plot op GraphicalDisplay
            IOSYNC
        }
    }

    

    DEC Y
    TSTZ Y
    JMPF SIMULATIE_STAP   ; Voer opeenvolgende diffusie-rondes uit

    HALT

    ; ==========================================================
    ;  PARALLELLE WARMTE WORKER (Puur Rekenwerk, Nul I/O)
    ; ==========================================================
    HEAT_WORKER:
        ; Register X bevat direct de unieke cel-index voor deze thread (0 t/m 399)
        0 -> A
        0 -> B
        0 -> I 

        ; --- GUARD 1a: Linker- en rechterrand (X % ROW_SIZE == 0 of X % ROW_SIZE == LAST_COL) ---
        X -> A
        ROW_SIZE -> B
        MOD A B

        IF (A ZERO) TRUE {
            A -> [grid_next + X]
            AUTOCLOSE
        }

        LAST_COL -> B
        IF (A == B) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- GUARD 1b: Bovenrand (X < ROW_SIZE) ---
        ROW_SIZE -> B
        IF (B > X) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- GUARD 1c: Onderrand (X >= BOTTOM_START) ---
        BOTTOM_START -> B
        DEC B                     ; B = 379; test of X > 379
        IF (X > B) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- GUARD 2: Permanente Warmtebron op cel HEAT_SOURCE (210) ---
        HEAT_SOURCE -> B
        IF (X == B) TRUE {
            70 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- 4-BUREN DIFFUSIE BEREKENING ---
        ; Noord-buur (X - ROW_SIZE)
        X -> A
        SUBI A ROW_SIZE
        [grid_current + A] -> A ; A = T_Noord (I wordt overschreven door LD I, A, maar X blijft veilig!)

        ; Zuid-buur (X + ROW_SIZE)
        X -> B
        ADDI B ROW_SIZE
        [grid_current + B] -> B ; B = T_Zuid
        ADD A B                 ; A = T_Noord + T_Zuid

        ; West-buur (X - 1)
        X -> B
        DEC B
        [grid_current + B] -> B ; B = T_West
        ADD A B                 ; A = T_Noord + T_Zuid + T_West

        ; Oost-buur (X + 1)
        X -> B
        INC B
        [grid_current + B] -> B ; B = T_Oost
        ADD A B                 ; A = Som van 4 buren

        ; Bereken afgerond gemiddelde (Som / 4)
        ADDI A 3
        DIVI A 4                ; A = Som // 4

        ; Schrijf het resultaat weg naar de OORSPRONKELIJKE cel X!
        A -> [grid_next + X]
        ; Just return A 
        AUTOCLOSE
}