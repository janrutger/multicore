MAP {
    MEMSIZE 2560
    START main

    ; === GEHEUGEN ALLOCATIE ===
    RES notused 513         ; Vult het Private Memory bereik (2048..2559) netjes op
    RES failcount 1         ; Teller voor gemiste spawns (Adres 2046)
    RES grid 400            ; Iteratie-resultaten per pixel (20x20 = 400 cellen)
    RES draw_ptr 1          ; Pointer voor interleaved display-rendering (0..400)

    ; === CONSTANTEN & SCHALEN ===
    CONST ROW_SIZE 20       ; Breedte en hoogte van het raster (20x20)
    CONST TOTAL_CELLS 400   ; Totaal aantal pixels
    CONST MAX_ITER 32       ; Maximale Mandelbrot iteratiediepte

    ; Fixed-Point Schaal (1000 = 1.000)
    CONST FP_SCALE 1000
    CONST FP_HALF 500
    CONST BAILOUT 4000      ; Ontsnappingsgrens |z|^2 > 4.0 (4.0 * 1000 = 4000)

    ; I/O Poorten voor GraphicalDisplay
    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2

    ; === HELPER MACRO'S ===
    MACRO scale(reg, scale_val) {
        MULI reg scale_val
    }

    MACRO dscale(reg, scale_val) {
        DIVI reg scale_val
    }

    MACRO fmul(Rx, Ry, scale_val) {
        MUL Rx, Ry
        DIVI Rx, scale_val
    }

    MACRO fmul_round(Rx, Ry, scale_val, half_val) {
        MUL Rx, Ry
        ADDI Rx, half_val
        DIVI Rx, scale_val
    }

    MACRO fdiv(Rx, denominator, scale_val) {
        MULI Rx, scale_val
        DIV Rx, denominator
    }

    MACRO waitMatrix() {
        _waitMatrix:
            ALLSYNC _waitMatrix
    }

    ; === GESTROOMTOONDE INTERLEAVED SPAWN MACRO (MET SUCCES FALLTHROUGH) ===
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task       ; 1. Probeer op buur-CPU via CIU
            SUCCES _spawnd

            CONTEXT arg task        ; 2. Probeer lokaal op CPU 0
            SUCCES _spawnd

        _count:
            ; 1. Verhoog failcount
            [failcount] -> A
            INC A
            A -> [failcount]

            ; 2. Haal huidige pointer op
            [draw_ptr] -> I

            ; 3. Probeer de pixel op index I te tekenen
            I -> A
            [grid + A] -> A         ; Lees resultaat uit Shared RAM

            IF (A ZERO) FALSE {
                MULI A 7            ; Schaal iteratie naar kleur
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

            ; 4. SCHUIF POINTER DOOR MET MODULO 400 (RING BUFFER)
            INC I
            TOTAL_CELLS -> B        ; B = 400
            MOD I B                 ; I = (I + 1) % 400
            I -> [draw_ptr]

            TOTAL_CELLS -> B        ; Herstel B op 400 voor de buitenste spawn-lus
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

    ; Initialiseer de GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; Reset tellers
    0 -> A
    A -> [failcount]
    A -> [draw_ptr]

    TOTAL_CELLS -> B        ; Stopgrens 400 voor de SPAWN lus

    ; ==========================================================
    ; 1. PARALLELLE SPAWN FASE (400 Mandelbrot Pixels Verdelen)
    ; ==========================================================
    REPEAT UNTIL (X == B) {
        startTask(MANDEL_WORKER, X)
        INC X
    }

    ; Wacht tot alle 4 Worker CPU's klaar zijn met hun taken
    waitMatrix()

    ; ==========================================================
    ; 2. RESTERENDE PIXELS VEGEN EN PLOTTEN NAAR SCHERM
    ; ==========================================================
    [draw_ptr] -> I
    TOTAL_CELLS -> B

    REPEAT UNTIL (I == B) {
        I -> A
        [grid + A] -> A

        IF (A ZERO) FALSE {
            MULI A 7        ; Kleur opschalen
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

        TOTAL_CELLS -> B
        INC I
    }

    waitMatrix()
    HALT

    ; ==========================================================
    ; 3. PARALLELLE MANDELBROT WORKER (Fixed-Point Schaal 1000)
    ; Input: Register X bevat de Pixel-Index (0 t/m 399)
    ; ==========================================================
    MANDEL_WORKER:
    0 -> A
    0 -> B
    0 -> C 
    0 -> K
    0 -> L 
    0 -> M 
    ; 0 -> X 
    0 -> Y
    0 -> Z

        ; --- A. COÖRDINATEN OMMAPPEN (Pixel Index -> Complex Vlak) ---
        ; cx = (px * 150) - 2000  ==> Bereik: [-2.000 t/m +0.850]
        X -> A
        ROW_SIZE -> B
        MOD A B             ; A = px (0..19)
        MULI A 150
        SUBI A 2000
        A -> C              ; C = cx (vastgehouden in C)

        ; cy = (py * 150) - 1350  ==> Bereik: [-1.350 t/m +1.500]
        X -> A
        DIVI A ROW_SIZE     ; A = py (0..19)
        MULI A 150
        SUBI A 1350
        A -> K              ; K = cy (vastgehouden in K)

        ; --- B. INITIALISEER ITERATIE Z = 0 + 0i ---
        0 -> L              ; L = zx = 0
        0 -> M              ; M = zy = 0
        0 -> Y              ; Y = iteratieteller = 0

    MANDEL_LOOP:
        ; --- C. BEREKEN zx^2 EN zy^2 (Met Fixed-Point Afronding) ---
        L -> A
        fmul_round(A, L, FP_SCALE, FP_HALF) ; A = zx_2

        M -> B
        fmul_round(B, M, FP_SCALE, FP_HALF) ; B = zy_2

        ; --- D. BAILOUT CHECK: zx_2 + zy_2 > 4000 (|z|^2 > 4.0) ---
        A -> Z
        ADD Z B             ; Z = zx_2 + zy_2
        BAILOUT -> I
        IF (Z > I) TRUE {
            JMP MANDEL_DONE ; Ontsnapt!
        }

        ; --- E. BEREKEN NIEUWE zy: zy_next = (2 * zx * zy) / 1000 + cy ---
        L -> Z              ; Z = zx
        fmul_round(Z, M, FP_SCALE, FP_HALF) ; Z = (zx * zy) / 1000
        MULI Z 2            ; Z = (2 * zx * zy) / 1000
        ADD Z K             ; Z = zy_next

        ; --- F. BEREKEN NIEUWE zx: zx_next = zx_2 - zy_2 + cx ---
        SUB A B             ; A = zx_2 - zy_2
        ADD A C             ; A = zx_next

        ; --- G. UPDATE Z-WAARDEN VOOR VOLGENDE ITERATIE ---
        A -> L              ; zx = zx_next
        Z -> M              ; zy = zy_next

        ; --- H. CHECK MAXIMALE DIEPTE ---
        INC Y               ; iter++
        MAX_ITER -> I
        IF (Y == I) TRUE {
            JMP MANDEL_DONE ; Maximale iteraties bereikt
        }

        JMP MANDEL_LOOP     ; Volgende iteratie stap

    MANDEL_DONE:
        ; --- I. OPSLAAN EN HARDWARE CONTEXT SLUITEN ---
        Y -> [grid + X]     ; Sla iteratie-aantal (kleur) op in Shared RAM
        AUTOCLOSE           ; Geef de uCores direct schoon terug aan de pool!
}