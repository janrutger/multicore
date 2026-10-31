MAP {
    MEMSIZE 1024
    START main

    RES grid_current 400    ; Huidige temperatuur-raster (20x20)
    RES grid_next 400       ; Buffer voor de berekende volgende stap
    RES draw_ptr 1          ; Pointer voor de interleaved display-renderer (0 t/m 400)

    CONST ROW_SIZE 20       ; Aantal kolommen
    CONST TOTAL_CELLS 400   ; Totale aantal cellen in het raster
    CONST GRID_SIZE 399     ; Laatste cel-index (400 cellen: 0 t/m 399)
    CONST LAST_COL 19       ; Rechterrand kolom-index
    CONST BOTTOM_START 380  ; Start-index van de onderste rij (19 * 20)
    CONST HEAT_SOURCE 210   ; Permanente warmtebron in het centrum 355

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

    ; ==========================================================
    ; INTERLEAVED SPAWN MACRO (MET HERSTELDE 400 BOUNDS-CHECK)
    ; ==========================================================
    MACRO startTask(task, arg){
        _spawntask:
            CONTEXT arg task
            FAIL _count
            JMP _spawnd

        _count:
            INC K                   ; Unieke FAIL-teller bijhouden

            [draw_ptr] -> I         ; Haal huidige pixel-pointer op (0..400)
            TOTAL_CELLS -> B        ; Stopgrens is 400 cellen!
            
            IF (I == B) TRUE {      ; Als I == 400 is (alle pixels al getekend):
                TOTAL_CELLS -> B    ; Herstel B (400) voor outer spawn-lus
                JMP _spawntask      ; Sla tekenen over, probeer spawn direct opnieuw
            }

            ; --- TEKEN 1 PIXEL TIJDENS DEZE FAIL ---
            I -> A                  ; Laad index I in Register A voor LDX!
            [grid_current + A] -> C ; Veilig lezen uit grid_current[I]

            ; Hoog pointer op in RAM voor de volgende FAIL
            INC I
            I -> [draw_ptr]
            DEC I                   ; Herstel I (0..399) voor coördinaatberekening

            IF (C ZERO) FALSE {
                DIVI C 5            ; Schaal temperatuur naar kleurpalet
                OUT C VAL             

                ; X-coördinaat: (I % 20) * 5
                I -> M
                ROW_SIZE -> A
                MOD M A
                MULI M 5
                OUT M X_POS

                ; Y-coördinaat: (I / 20) * 5
                I -> M
                DIVI M ROW_SIZE
                MULI M 5
                OUT M Y_POS

                PLOT_CMD -> A
                OUT A CMD           ; Trigger plot op GraphicalDisplay
                IOSYNC
            }

            TOTAL_CELLS -> B        ; Herstel B (400) voor outer spawn-lus
            JMP _spawntask          ; Probeer worker opnieuw te spawnen

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
    0 -> C 
    0 -> M 

    ; Initialiseer de grafische display-bus 1x op de Master-CPU
    GRAPH_DEV -> A
    OUT A DEV

    ; --- 1. INITIALISATIE VAN HET RASTER ---
    REPEAT I TIMES GRID_SIZE {
        A -> [grid_current + I]
        A -> [grid_next + I]
    }

    ; Permanente warmtebron op cel 355 (temperatuur 70)
    70 -> A
    HEAT_SOURCE -> I
    A -> [grid_current + I]

    ; ==========================================================
    ;  HOOFD SIMULATIE LUS (150 diffusie-stappen)
    ; ==========================================================
    150 -> Y                 ; Simulatierondes

SIMULATIE_STAP:
    0 -> X                 ; Start bij cel 0 voor de SPAWN pijplijn
    0 -> A
    A -> [draw_ptr]        ; Reset display-pointer op 0 voor dit nieuwe frame
    TOTAL_CELLS -> B       ; B op 400 zetten zodat X exact 0 t/m 399 doorloopt

    ; --- 2. PARALLELLE REKEN-FASE + INTERLEAVED RENDERING ---
    REPEAT UNTIL (X == B) {
        startTask(HEAT_WORKER, X)
        INC X    
    }
    waitMatrix()

    ; --- 3. SWEEP REMAINING PIXELS (Veiligheidsslag) ---
    [draw_ptr] -> I
    TOTAL_CELLS -> B       ; Stopgrens 400
    REPEAT UNTIL (I == B) {
        I -> A             ; Index I expliciet in Register A laden voor LDX!
        [grid_current + A] -> C

        IF (C ZERO) FALSE {
            DIVI C 5
            OUT C VAL             

            I -> M
            ROW_SIZE -> A
            MOD M A
            MULI M 5
            OUT M X_POS

            I -> M
            DIVI M ROW_SIZE
            MULI M 5
            OUT M Y_POS

            PLOT_CMD -> A
            OUT A CMD             
            IOSYNC
        }
        INC I
    }

    ; --- 4. SWAP BUFFERS ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_next + I] -> C    ; Gebruik C om Register A (index) intact te houden!
        C -> [grid_current + I]
    }

    DEC Y
    TSTZ Y
    JMPF SIMULATIE_STAP

    waitMatrix()
    HALT

    ; ==========================================================
    ;  PARALLELLE WARMTE WORKER (FULL TORUS + 4 KOUDE HOEKEN)
    ; ==========================================================
    HEAT_WORKER:
        0 -> A
        0 -> B
        0 -> I
        0 -> M

        ; --- GUARD 1: De 4 Koude Hoekpunten ---
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

        ; --- GUARD 2: Permanente Warmtebron ---
        HEAT_SOURCE -> B
        IF (X == B) TRUE {
            70 -> A
            A -> [grid_next + X]
            AUTOCLOSE
        }

        ; --- 4-BUREN DIFFUSIE MET FULL TORUS-WRAPPING ---

        ; 1. Noord-buur
        X -> A
        SUBI A ROW_SIZE         ; A = X - 20
        ROW_SIZE -> B
        IF (B > X) TRUE {       ; Bovenrand
            ADDI A 400
        }
        [grid_current + A] -> A ; A = T_Noord

        ; 2. Zuid-buur
        X -> B
        ADDI B ROW_SIZE         ; B = X + 20
        BOTTOM_START -> M
        DEC M                   ; M = 379
        IF (X > M) TRUE {       ; Onderrand
            SUBI B 400
        }
        [grid_current + B] -> B ; B = T_Zuid
        ADD A B                 ; A = T_Noord + T_Zuid

        ; 3. West-buur
        X -> M
        ROW_SIZE -> B
        MOD M B                 ; M = X % 20
        X -> B
        DEC B                   ; B = X - 1
        IF (M ZERO) TRUE {      ; Linkerkolom
            ADDI B 20
        }
        [grid_current + B] -> B ; B = T_West
        ADD A B                 ; A = T_Noord + T_Zuid + T_West

        ; 4. Oost-buur
        X -> M
        ROW_SIZE -> B
        MOD M B                 ; M = X % 20
        SUBI M 19               ; Rechterkolom check
        X -> B
        INC B                   ; B = X + 1
        IF (M ZERO) TRUE {      ; Rechterkolom
            SUBI B 20
        }
        [grid_current + B] -> B ; B = T_Oost
        ADD A B                 ; A = Som van 4 buren

        ; Gemiddelde afronden (Som + 3) / 4
        ADDI A 3
        DIVI A 4

        A -> [grid_next + X]
        AUTOCLOSE
}