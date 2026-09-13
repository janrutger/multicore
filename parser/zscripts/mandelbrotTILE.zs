MAP {
    MEMSIZE 2560
    START main

    ; === GEHEUGEN ALLOCATIE ===
    RES notused 513         ; RAM opvullen voor private boundary
    RES tile_x_glob 1       ; Globale X-offset van de huidige tegel in RAM
    RES tile_y_glob 1       ; Globale Y-offset van de huidige tegel in RAM
    RES grid 12             ; Beproefde tegelbuffer: EXACT 12 woorden (3x4)

    ; === CANVAS & TEGEL CONFIGURATIE ===
    CONST IMG_WIDTH 204      ; Totale canvas breedte (deelbaar door 3)
    CONST IMG_HEIGHT 204     ; Totale canvas hoogte (deelbaar door 4)
    
    CONST TILE_W 3          ; Tegel breedte = 3
    CONST TILE_H 4          ; Tegel hoogte = 4
    CONST TILE_PIXELS 12    ; 3 x 4 = 12 pixels per tegel (100% HW match!)

    CONST MAX_ITER 32       ; Maximale Mandelbrot iteratiediepte

    ; Fixed-Point Schaal (1000 = 1.000)
    CONST FP_SCALE 1000
    CONST FP_HALF 500
    CONST BAILOUT 4000      ; Ontsnappingsgrens |z|^2 > 4.0

    ; I/O Poorten voor GraphicalDisplay
    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2

    ; === MACRO'S ===
    MACRO waitMatrix() {
        _waitMatrix:
            ALLSYNC _waitMatrix
    }

    MACRO fmul_round(Rx, Ry, scale_val, half_val) {
        MUL Rx, Ry
        ADDI Rx, half_val
        DIVI Rx, scale_val
    }

    ; Strakke Task-Dispatcher
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task       ; 1. Probeer op buur-CPU via CIU
            SUCCES _spawnd

            CONTEXT arg task        ; 2. Probeer lokaal op CPU 0
            SUCCES _spawnd

            JMP _spawntask          ; Herhaal indien even bezet
        _spawnd:
    }
}

PROGRAM {
main:
    0 -> A
    0 -> I
    0 -> B
    0 -> L
    0 -> X

    ; Initialiseer de GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; Sla lus-grenzen op in geldige registers (L is vrij in main!)
    IMG_HEIGHT -> L                 ; L = 36 (Hoogte grens)
    IMG_WIDTH -> K                  ; K = 36 (Breedte grens)
    TILE_PIXELS -> M                ; M = 12 (Tegel grens)

    ; ==========================================================
    ; HOOFD TEGEL-LUS (Loop over alle 3x4 tegels van het beeld)
    ; ==========================================================
    0 -> I                          ; I = Tile Y-Offset
    REPEAT UNTIL (I == L) {
        I -> [tile_y_glob]

        0 -> B                      ; B = Tile X-Offset
        REPEAT UNTIL (B == K) {
            B -> [tile_x_glob]

            ; --- 1. SPAWN DE 12 WORKERS VOOR DEZE TEGEL (Index 0 t/m 11) ---
            0 -> X
            REPEAT UNTIL (X == M) {
                startTask(MANDEL_WORKER, X)
                INC X
            }

            ; --- 2. WACHT TOT DEZE TEGEL (12 PIXELS) KLAAR IS ---
            waitMatrix()

            ; --- 3. BATCH SWEEP: TEKEN DE 12 PIXELS VAN DEZE TEGEL ---
            0 -> X
            REPEAT UNTIL (X == M) {
                X -> A
                [grid + A] -> A      ; Lees aantal iteraties voor tegelpixel X

                IF (A ZERO) FALSE {
                    MAX_ITER -> C
                    IF (A == C) TRUE {
                        0 -> A       ; Binnenkant krijgt kleur 0 (zwart)
                    }

                    MULI A 7         ; Schaal iteraties naar kleur-index
                    OUT A VAL

                    ; Bereken absolute X-positie op scherm = tile_x_glob + (X % 3)
                    [tile_x_glob] -> A
                    X -> C
                    3 -> Z
                    MOD C Z          ; C = X % 3
                    ADD A C          ; A = tile_x + (X % 3)
                    MULI A 2         ; Scherm-schaal (8x8 pixels per cel op display)
                    OUT A X_POS

                    ; Bereken absolute Y-positie op scherm = tile_y_glob + (X / 3)
                    [tile_y_glob] -> A
                    X -> C
                    3 -> Z
                    DIV C Z         ; C = X / 3
                    ADD A C          ; A = tile_y + (X / 3)
                    MULI A 2         ; Scherm-schaal (8x8 pixels per cel op display)
                    OUT A Y_POS

                    PLOT_CMD -> A
                    OUT A CMD
                    IOSYNC
                }

                INC X
            }

            ; Schuif Tile X-Offset 3 kolommen op
            [tile_x_glob] -> B
            3 -> A
            ADD B A
            B -> [tile_x_glob]

            IMG_WIDTH -> K          ; Herstel grens K = 36
        }

        ; Schuif Tile Y-Offset 4 rijen op
        [tile_y_glob] -> I
        4 -> A
        ADD I A
        I -> [tile_y_glob]

        IMG_HEIGHT -> L             ; Herstel grens L = 36
    }

    waitMatrix()
    HALT

    ; ==========================================================
    ; PARALLELLE MANDELBROT TEGEL-WORKER (Fixed-Point Schaal 1000)
    ; Input: Register X bevat de lokale tegel-index (0 t/m 11)
    ; ==========================================================
    MANDEL_WORKER:
        0 -> A
        0 -> B
        0 -> C 
        0 -> K
        0 -> L 
        0 -> M 
        0 -> Y
        0 -> Z

        ; --- A. BEREKEN ABSOLUTE PX EN PY COÖRDINATEN ---
        ; local_px = X % 3
        X -> A
        3 -> B                       ; TILE_W = 3
        MOD A B                      ; A = local_px

        ; global_px = tile_x_glob + local_px
        [tile_x_glob] -> B
        ADD A B                      ; A = global_px (0 t/m 35)

        ; cx = (global_px * 80) - 2000  ==> Bereik [-2.000 t/m +0.800]
        MULI A 14      ; 36x36 = 80
        SUBI A 2000
        A -> C                       ; C = cx

        ; local_py = X / 3
        X -> A
        3 -> B                       ; TILE_W = 3
        DIV A B                     ; A = local_py

        ; global_py = tile_y_glob + local_py
        [tile_y_glob] -> B
        ADD A B                      ; A = global_py (0 t/m 35)

        ; cy = (global_py * 80) - 1400  ==> Bereik [-1.400 t/m +1.400]
        MULI A 14
        SUBI A 1400
        A -> K                       ; K = cy

        ; --- B. INITIALISEER ITERATIE Z = 0 + 0i ---
        0 -> L                       ; zx = 0
        0 -> M                       ; zy = 0
        0 -> Y                       ; iteratieteller = 0

    MANDEL_LOOP:
        ; --- C. BEREKEN zx^2 EN zy^2 ---
        L -> A
        fmul_round(A, L, FP_SCALE, FP_HALF) ; A = zx_2

        M -> B
        fmul_round(B, M, FP_SCALE, FP_HALF) ; B = zy_2

        ; --- D. BAILOUT CHECK: zx_2 + zy_2 > 4000 ---
        A -> Z
        ADD Z B                      ; Z = zx_2 + zy_2
        BAILOUT -> I
        IF (Z > I) TRUE {
            JMP MANDEL_DONE          ; Ontsnapt!
        }

        ; --- E. BEREKEN NIEUWE zy ---
        L -> Z                       ; Z = zx
        fmul_round(Z, M, FP_SCALE, FP_HALF) ; Z = (zx * zy) / 1000
        MULI Z 2                     ; Z = (2 * zx * zy) / 1000
        ADD Z K                      ; Z = zy_next

        ; --- F. BEREKEN NIEUWE zx ---
        SUB A B                      ; A = zx_2 - zy_2
        ADD A C                      ; A = zx_next

        ; --- G. UPDATE Z-WAARDEN ---
        A -> L                       ; zx = zx_next
        Z -> M                       ; zy = zy_next

        ; --- H. CHECK MAXIMALE DIEPTE ---
        INC Y                        ; iter++
        MAX_ITER -> I
        IF (Y == I) TRUE {
            JMP MANDEL_DONE
        }

        JMP MANDEL_LOOP

    MANDEL_DONE:
        ; --- I. OPSLAAN IN TEGELBUFFER EN AUTOCLOSE ---
        Y -> [grid + X]              ; Sla op op lokale tegel-index X (0..11)
        AUTOCLOSE
}