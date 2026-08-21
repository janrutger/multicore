MAP {
    MEMSIZE 1024
    START main

    RES failcount 1

    RES grid_current 400    ; Huidige temperatuur-raster (20x20)
    RES grid_next 400       ; Buffer voor de berekende volgende stap
    RES draw_ptr 1          ; Pointer voor de interleaved display-renderer (0 t/m 400)

    RES itterations 1

    CONST ROW_SIZE 20       ; Aantal kolommen
    CONST TOTAL_CELLS 400   ; Totale aantal cellen in het raster
    CONST GRID_SIZE 399     ; Laatste cel-index (400 cellen: 0 t/m 399)
    CONST LAST_COL 19       ; Rechterrand kolom-index
    CONST BOTTOM_START 380  ; Start-index van de onderste rij (19 * 20)
    CONST HEAT_SOURCE 350   ; Permanente warmtebron in het centrum 210, 350

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
    ; INTERLEAVED SPAWN MACRO (GEOPTIMALISEERD: ZONDER C EN M)
    ; ==========================================================
    MACRO startTask(task, arg){
        _spawntask:
            CONTEXT arg task
            FAIL _count
            JMP _spawnd

        _count:
            ; INC K                   ; Unieke FAIL-teller bijhouden
            [failcount] -> A 
            INC A 
            A -> [failcount]

            [draw_ptr] -> I         ; Haal huidige pixel-pointer op (0..400)
            TOTAL_CELLS -> B        ; Stopgrens 400
            
            IF (I == B) TRUE {      ; Als I == 400 is (alle pixels al getekend):
                TOTAL_CELLS -> B    ; Herstel B (400) voor outer spawn-lus
                JMP _spawntask      ; Sla tekenen over, probeer spawn direct opnieuw
            }

            ; --- TEKEN 1 PIXEL TIJDENS DEZE FAIL (GEBRUIKT ALLEEN A EN B) ---
            I -> A                  
            [grid_current + A] -> A ; Lees temperatuur rechtstreeks in A

            ; Hoog pointer op in RAM voor de volgende FAIL
            INC I
            I -> [draw_ptr]
            DEC I                   ; Herstel I (0..399) voor coördinaatberekening

            IF (A ZERO) FALSE {
                DIVI A 5            ; Schaal temperatuur naar kleurpalet
                OUT A VAL           ; Stuur kleur direct weg

                ; X-coördinaat: (I % 20) * 5
                I -> A
                ROW_SIZE -> B
                MOD A B             ; A = I % 20
                MULI A 5
                OUT A X_POS         ; Stuur X-positie weg

                ; Y-coördinaat: (I / 20) * 5
                I -> A
                DIVI A ROW_SIZE     ; A = I / 20
                MULI A 5
                OUT A Y_POS         ; Stuur Y-positie weg

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
    ; 0 -> Y 
    ; 0 -> K                  ; Slechts 6 registers in gebruik in main!

    ; Initialiseer de grafische display-bus 1x op de Master-CPU
    GRAPH_DEV -> A
    OUT A DEV

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
    ;  HOOFD SIMULATIE LUS (150 diffusie-stappen)
    ; ==========================================================
    150 -> A                 ; Simulatierondes
    A -> [itterations]

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

    ; --- 3. SWEEP REMAINING PIXELS (ZONDER C EN M) ---
    [draw_ptr] -> I
    TOTAL_CELLS -> B       ; Stopgrens 400
    REPEAT UNTIL (I == B) {
        I -> A             
        [grid_current + A] -> A

        IF (A ZERO) FALSE {
            DIVI A 5
            OUT A VAL             

            I -> A
            ROW_SIZE -> B
            MOD A B
            MULI A 5
            OUT A X_POS

            I -> A
            DIVI A ROW_SIZE
            MULI A 5
            OUT A Y_POS

            PLOT_CMD -> A
            OUT A CMD             
            IOSYNC
        }
        TOTAL_CELLS -> B   ; Herstel B op 400 voor de REPEAT UNTIL voorwaarde
        INC I
    }

    ; --- 4. SWAP BUFFERS ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_next + I] -> A
        A -> [grid_current + I]
    }

    ; DEC Y
    ; TSTZ Y
    [itterations] -> A 
    DEC A 
    A ->[itterations]

    TSTZ A
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