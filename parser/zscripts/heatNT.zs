MAP {
    MEMSIZE 2560
    START main

    RES grid_current 100    ; Huidige temperatuur-raster (10x10)
    RES grid_next 100       ; Buffer voor de berekende volgende stap

    CONST GRID_SIZE 99
    CONST ROW_SIZE 10

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
    0 -> A
    0 -> I
    0 -> B
    0 -> M
    0 -> X
    0 -> Y 

    REPEAT I TIMES GRID_SIZE {
        A -> [grid_current + I]
        A -> [grid_next + I]
    }

    ; Permanente warmtebron (temperatuur 7 = Geel/Cyan) op cel 45
    70 -> A
    45 -> I
    A -> [grid_current + I]

    ; ==========================================================
    ;  HOOFD SIMULATIE LUS (Draait N diffusie-stappen)
    ; ==========================================================
    
    30 -> Y            ; Y telt de simulatierondes (itteraties)
SIMULATIE_STAP:
    
    0 -> X             ; Start-index X bij cel 0 voor de SPAWN pijplijn
    GRID_SIZE -> B

    ; --- 2. PARALLELLE REKEN-FASE (32 uCores Matrix) ---
    SPAWN HEAT_WORKER X UNTIL (X == B) TRUE UPDATE {
        INC X
    } HARVEST A {
        ; Enkel uCore vrijmaken; resultaat staat al decentraal in grid_next
    }

    ; --- 3. SERIËLE IN-ORDER DISPLAY-FASE (Master CPU) ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_next + I] -> C


        ; SLIMME I/O FILTER: Verstuur ALLEEN als de temperatuur > 0 is!
        IF (C ZERO) FALSE {
            GRAPH_DEV -> A
            PLOT_CMD  -> B

            OUT A DEV
            DIVI C 5              ; scale de waarde naar kleuren
            OUT C VAL             ; Kleurcode op basis van temperatuur (1 t/m 7)

            ; Scherm X-coördinaat: (I % 10) * 10 pixels
            I -> M
            ROW_SIZE -> A
            MOD M A
            MULI M 10
            OUT M X_POS

            ; Scherm Y-coördinaat: (I / 10) * 10 pixels
            I -> M
            DIVI M ROW_SIZE
            MULI M 10
            OUT M Y_POS

            OUT B CMD             ; Trigger plot op GraphicalDisplay
            IOSYNC
        }
    }
    

    ; --- 4. SWAP BUFFERS (Kopieer grid_next naar grid_current) ---
    0 -> I
    REPEAT I TIMES GRID_SIZE {
        [grid_next + I] -> A
        A -> [grid_current + I]
    }

    DEC Y
    TSTZ Y
    JMPF SIMULATIE_STAP   ; Voer 15 opeenvolgende diffusie-rondes uit

    HALT



    ; ==========================================================
    ;  PARALLELLE WARMTE WORKER (Puur Rekenwerk, Nul I/O)
    ; ==========================================================
    HEAT_WORKER:
        ; Register X bevat direct de unieke cel-index voor deze thread (0 t/m 99)
        0 -> A
        0 -> B
        0 -> I 

        ; --- GUARD 1a: Linker- en rechterrand (X % 10 == 0 of X % 10 == 9) ---
        X -> A
        ROW_SIZE -> B
        MOD A B

        IF (A ZERO) TRUE {
            A -> [grid_next + X]
            CLOSE
        }

        9 -> B
        IF (A == B) TRUE {
            0 -> A
            A -> [grid_next + X]
            CLOSE
        }

        ; --- GUARD 1b: Bovenrand (X < 10) ---
        10 -> B
        IF (B > X) TRUE {
            0 -> A
            A -> [grid_next + X]
            CLOSE
        }

        ; --- GUARD 1c: Onderrand (X >= 90) ---
        89 -> B
        IF (X > B) TRUE {
            0 -> A
            A -> [grid_next + X]
            CLOSE
        }

        ; --- GUARD 2: Permanente Warmtebron op cel 45 ---
        45 -> B
        IF (X == B) TRUE {
            70 -> A
            A -> [grid_next + X]
            CLOSE
        }




        ; --- 4-BUREN DIFFUSIE BEREKENING ---
        ; Noord-buur (X - 10)
        X -> A
        SUBI A 10
        [grid_current + A] -> A ; A = T_Noord (I wordt overschreven door LD I, A, maar X blijft veilig!)

        ; Zuid-buur (X + 10)
        X -> B
        ADDI B 10
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
        CLOSE
}