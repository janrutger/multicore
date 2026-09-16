MAP {
    MEMSIZE 1024
    START main

    RES grid_current 400    ; Huidige temperatuur-raster (20x20)
    RES grid_next 400       ; Buffer voor de berekende volgende stap

    CONST ROW_SIZE 20       ; Aantal kolommen
    CONST GRID_SIZE 399     ; Laatste cel-index (400 cellen: 0 t/m 399)
    CONST LAST_COL 19       ; Rechterrand kolom-index
    CONST BOTTOM_START 380  ; Start-index van de onderste rij (19 * 20)
    CONST HEAT_SOURCE 355   ; Permanente warmtebron in het centrum (10, 10) 210

    ; De 4 hoekpunten als koude-sinks (temperatuur 0)
    CONST CORNER_TL 0       ; Boven-Links
    CONST CORNER_TR 19      ; Boven-Rechts
    CONST CORNER_BL 380     ; Onder-Links
    CONST CORNER_BR 399     ; Onder-Rechts

    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2

    MACRO waitMatrix() {
        _waitMatrix:
        SYNC _waitMatrix
    }

    MACRO startTask(task, arg){
        _spawntask:
            CONTEXT arg task
            FAIL _count
            JMP _spawnd

        _count:
            INC K
            JMP _spawntask

        _spawnd:
    }
}

PROGRAM {
main:
    0 -> A
    0 -> I
    0 -> B
    0 -> X
    0 -> Y 

    0 -> K

    ; --- 1. INITIALISATIE VAN HET RASTER ---
    REPEAT I TIMES GRID_SIZE {
        A -> [grid_current + I]
        A -> [grid_next + I]
    }

    ; Permanente warmtebron op cel 210 (temperatuur 70)
    70 -> A
    HEAT_SOURCE -> I
    A -> [grid_current + I]

    ; ==========================================================
    ;  HOOFD SIMULATIE LUS (Draait 75 diffusie-stappen)
    ; ==========================================================
    150 -> Y                 ; Y telt de simulatierondes

SIMULATIE_STAP:
    0 -> X                 ; Start bij cel 0 voor de SPAWN pijplijn
    GRID_SIZE -> B

    ; --- 2. PARALLELLE REKEN-FASE (32 uCores Matrix) ---
    REPEAT UNTIL (X == B) {
        startTask(HEAT_WORKER, X)
        INC X    
    }
    waitMatrix()

    ; --- 3. SWAP BUFFERS ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_next + I] -> A
        A -> [grid_current + I]
    }

    ; --- 4. Spawn DISPLAY worker ---
    0 -> I
    startTask(DISPLAY_WORKER, I)

    DEC Y
    TSTZ Y
    JMPF SIMULATIE_STAP

    waitMatrix()
    HALT

    ; ==========================================================
    ; DISPLAY WORKER (Puur I/O - Geoptimaliseerd)
    ; ==========================================================
    DISPLAY_WORKER:
        0 -> C 
        0 -> M 

        GRAPH_DEV -> A
        PLOT_CMD  -> B
        OUT A DEV

        REPEAT I TIMES GRID_SIZE {
            [grid_current + I] -> C

            IF (C ZERO) FALSE {
                DIVI C 5              ; Schaal temperatuur naar kleurpalet default=5
                OUT C VAL             

                ; Scherm X-coördinaat
                I -> M
                ROW_SIZE -> A
                MOD M A
                MULI M 5
                OUT M X_POS

                ; Scherm Y-coördinaat
                I -> M
                DIVI M ROW_SIZE
                MULI M 5
                OUT M Y_POS

                OUT B CMD             ; Trigger plot
                IOSYNC
            }
        }
        AUTOCLOSE

    ; ==========================================================
    ;  PARALLELLE WARMTE WORKER (FULL TORUS + 4 KOUDE HOEKEN)
    ; ==========================================================
    HEAT_WORKER:
        0 -> A
        0 -> B
        0 -> I
        0 -> M

        ; --- GUARD 1: De 4 Koude Hoekpunten (Vast op temperatuur 0) ---
        CORNER_TL -> B
        IF (X == B) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        CORNER_TR -> B
        IF (X == B) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        CORNER_BL -> B
        IF (X == B) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        CORNER_BR -> B
        IF (X == B) TRUE {
            0 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- GUARD 2: Permanente Warmtebron (Cel 210 op temperatuur 70) ---
        HEAT_SOURCE -> B
        IF (X == B) TRUE {
            70 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- 4-BUREN DIFFUSIE MET FULL TORUS-WRAPPING ---

        ; 1. Noord-buur (Bovenrand wrapt naar Onderste rij)
        X -> A
        SUBI A ROW_SIZE         ; A = X - 20
        ROW_SIZE -> B
        IF (B > X) TRUE {       ; Als X op bovenste rij zit (X < 20)
            ADDI A 400          ; Index = X - 20 + 400
        }
        [grid_current + A] -> A ; A = T_Noord

        ; 2. Zuid-buur (Onderrand wrapt naar Bovenste rij)
        X -> B
        ADDI B ROW_SIZE         ; B = X + 20
        BOTTOM_START -> M
        DEC M                   ; M = 379
        IF (X > M) TRUE {       ; Als X op onderste rij zit (X >= 380)
            SUBI B 400          ; Index = X + 20 - 400
        }
        [grid_current + B] -> B ; B = T_Zuid
        ADD A B                 ; A = T_Noord + T_Zuid

        ; 3. West-buur (Zonder register C)
        X -> M
        ROW_SIZE -> B
        MOD M B                 ; M = X % 20
        X -> B
        DEC B                   ; B = X - 1
        IF (M ZERO) TRUE {      ; Linkerkolom (X % 20 == 0)
            ADDI B 20           ; Wrap naar rechterkolom
        }
        [grid_current + B] -> B ; B = T_West
        ADD A B                 ; A = T_Noord + T_Zuid + T_West

        ; 4. Oost-buur (Zonder register C)
        X -> M
        ROW_SIZE -> B
        MOD M B                 ; M = X % 20
        SUBI M 19               ; M = 0 als X op rechterkolom (19) zit
        X -> B
        INC B                   ; B = X + 1
        IF (M ZERO) TRUE {      ; Rechterkolom
            SUBI B 20           ; Wrap naar linkerkolom
        }
        [grid_current + B] -> B ; B = T_Oost
        ADD A B                 ; A = Som van 4 buren

        ; Bereken afgerond gemiddelde (Som / 4)
        ADDI A 3
        DIVI A 4                ; A = Som // 4

        ; Schrijf resultaat weg
        A -> [grid_next + X]
        AUTOCLOSE
}