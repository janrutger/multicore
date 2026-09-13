MAP {
    MEMSIZE 2560
    START main

    ; === GEHEUGEN ALLOCATIE ===
    RES notused 512         ; Vult Private RAM (2048..2559) netjes op
    RES cur_pixel 1         ; Volgende pixel-index die uitgedeeld moet worden (Adres 2047)
    RES active_count 1      ; Aantal actieve workers op dit moment (Adres 2046)

    ; === 12 MAILBOX SLOTS IN SHARED RAM ===
    RES mb_px 12            ; Globale X-coördinaat per slot (Adres 2034..2045)
    RES mb_py 12            ; Globale Y-coördinaat per slot (Adres 2022..2033)
    RES mb_color 12         ; Berekend iteratie-resultaat per slot (Adres 2010..2021)
    RES mb_status 12        ; Status vlag per slot: 0=EMPTY, 1=BUSY, 2=DONE (Adres 1998..2009)

    ; === CANVAS & MAILBOX CONFIGURATIE ===
    CONST IMG_WIDTH 200      ; Totale canvas breedte
    CONST IMG_HEIGHT 200     ; Totale canvas hoogte
    CONST TOTAL_PIXELS 40000 ; 36 x 36 = 1296 pixels totaal
    CONST SLOTS 12          ; 12 Mailbox slots (4 Worker CPU's x 3 contexten)

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
    MACRO fmul_round(Rx, Ry, scale_val, half_val) {
        MUL Rx, Ry
        ADDI Rx, half_val
        DIVI Rx, scale_val
    }

    ; Task-Dispatcher
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task       ; 1. Probeer remote worker via CIU
            SUCCES _spawnd

            CONTEXT arg task        ; 2. Probeer lokaal op CPU 0
            SUCCES _spawnd

            JMP _spawntask          ; Herhaal indien bezet
        _spawnd:
    }
}

PROGRAM {
main:
    0 -> A
    0 -> I
    0 -> B
    0 -> C
    0 -> K
    0 -> L
    0 -> M
    0 -> X
    0 -> Y
    0 -> Z

    ; Initialiseer de GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; Sla constanten op in registers voor vergelijkingen
    TOTAL_PIXELS -> K               ; K = 1296
    SLOTS -> M                      ; M = 12

    ; Initialiseer globale tellers
    0 -> A
    A -> [cur_pixel]
    A -> [active_count]

    ; Initialiseer alle 12 mailbox status-slots op 0 (EMPTY)
    0 -> X
    REPEAT UNTIL (X == M) {
        0 -> A
        A -> [mb_status + X]
        INC X
        SLOTS -> M                  ; Herstel M = 12
    }

    ; ==========================================================
    ; SPSC MAILBOX STREAMING MAIN LOOP (Geen ALLSYNC meer!)
    ; ==========================================================
MAIN_STREAM_LOOP:
    0 -> X                          ; Poll slots X = 0 t/m 11
    REPEAT UNTIL (X == M) {

        ; --- STAP 1: CHECK OF SLOT X KLAAR IS (status == 2 / DONE) ---
        [mb_status + X] -> A
        2 -> B
        IF (A == B) TRUE {
            ; 1. Lees kleur en coördinaten uit mailbox-slot X
            [mb_color + X] -> A      ; A = iteratie-aantal (0..32)
            [mb_px + X] -> B         ; B = global_px (0..35)
            [mb_py + X] -> C         ; C = global_py (0..35)

            ; 2. Bepaal kleur en stuur direct naar GraphicalDisplay
            MAX_ITER -> Z            ; Z = 32
            IF (A == Z) TRUE {
                0 -> A               ; Binnenkant Mandelbrot krijgt kleur 0 (zwart)
            }
            IF (A == Z) FALSE {
                MULI A 7             ; Gradiënt voor ontsnapte punten
            }
            OUT A VAL

            B -> A
            MULI A 2                 ; Scherm-schaal (5x5 pixels op display)
            OUT A X_POS

            C -> A
            MULI A 2                 ; Scherm-schaal
            OUT A Y_POS

            PLOT_CMD -> A
            OUT A CMD
            IOSYNC

            ; 3. Markeer slot X als EMPTY (0)
            0 -> A
            A -> [mb_status + X]

            ; 4. Verlaag active_count
            [active_count] -> A
            DEC A
            A -> [active_count]
        }

        ; --- STAP 2: CHECK OF SLOT X LEEG IS (status == 0 / EMPTY) ---
        [mb_status + X] -> A
        ; TSTZ A
        IF (A ZERO) TRUE {
            ; Check of er nog onverwerkte pixels zijn (1296 > cur_pixel)
            [cur_pixel] -> A
            TOTAL_PIXELS -> K        ; K = 1296
            IF (K > A) TRUE {
                ; A bevat de huidige cur_pixel (0..1295)
                ; Bereken px = cur_pixel % 36
                A -> B
                IMG_WIDTH -> Z
                MOD B Z              ; B = px (0..35)
                B -> [mb_px + X]

                ; Bereken py = cur_pixel / 36
                A -> B
                IMG_WIDTH -> Z
                DIV B Z              ; B = py (0..35)
                B -> [mb_py + X]

                ; Markeer slot X direct als BUSY (1)
                1 -> B
                B -> [mb_status + X]

                ; Hoog cur_pixel op
                INC A
                A -> [cur_pixel]

                ; Hoog active_count op
                [active_count] -> B
                INC B
                B -> [active_count]

                ; Bescherm X op CPU 0: Kopieer slot-index naar Y en spawn Y!
                X -> Y
                startTask(MANDEL_WORKER, Y)
            }
        }

        INC X
        SLOTS -> M                   ; Herstel M = 12
    }

    ; --- STAP 3: CHECK EINDCONDITIE (cur_pixel == 1296 AND active_count == 0) ---
    [cur_pixel] -> A
    TOTAL_PIXELS -> K                ; K = 1296
    IF (A == K) TRUE {
        [active_count] -> B
        ; TSTZ B
        IF (B ZERO) TRUE {
            JMP STREAM_DONE          ; Alle 1296 pixels verwerkt én getekend!
        }
    }

    JMP MAIN_STREAM_LOOP

STREAM_DONE:
    HALT

    ; ==========================================================
    ; STREAMING MANDELBROT WORKER
    ; Input: Register Y bevat de toegewezen slot-index (0 t/m 11)
    ; ==========================================================
    MANDEL_WORKER:
        0 -> I
        ; Y -> I
        0 -> A
        0 -> B
        0 -> C 
        0 -> K
        0 -> L 
        0 -> M 
        0 -> Z
        ; Register Y bevat het slot-ID (0..11) en blijft intact!

        ; --- A. LEES GLOBAL PX EN PY UIT MAILBOX SLOT Y ---
        [mb_px + Y] -> A            ; A = global_px (0..35)
        MULI A 14                   ; (36x36=80) (100x100=28) (200x200=14)
        SUBI A 2000
        A -> C                      ; C = cx = (global_px * 80) - 2000

        [mb_py + Y] -> A            ; A = global_py (0..35)
        MULI A 14                   ; (36x36=80) (100x100=28) (200x200=14)
        SUBI A 1400
        A -> K                      ; K = cy = (global_py * 80) - 1400

        ; --- B. INITIALISEER Z = 0 + 0i ---
        ; 0 -> L                      ; zx = 0
        ; 0 -> M                      ; zy = 0
        ; 0 -> Z                      ; Z = iteratieteller = 0

    MANDEL_LOOP:
        ; --- C. BEREKEN zx^2 EN zy^2 ---
        L -> A
        fmul_round(A, L, FP_SCALE, FP_HALF) ; A = zx_2

        M -> B
        fmul_round(B, M, FP_SCALE, FP_HALF) ; B = zy_2

        ; --- D. BEREKEN NIEUWE zx EN SOM (BEWAART B ALS zy_2) ---
        A -> I
        ADD I B                      ; I = zx_2 + zy_2 (Som voor bailout)
        SUB A B                      ; A = zx_2 - zy_2
        ADD A C                      ; A = zx_next

        ; --- E. BAILOUT CHECK: zx_2 + zy_2 > 4000 ---
        BAILOUT -> B                 ; B is nu vrij en krijgt 4000
        IF (I > B) TRUE {
            JMP MANDEL_DONE          ; Ontsnapt!
        }

        ; --- F. BEREKEN NIEUWE zy ---
        L -> I                       ; I = zx
        fmul_round(I, M, FP_SCALE, FP_HALF) ; I = (zx * zy) / 1000
        MULI I 2                     ; I = (2 * zx * zy) / 1000
        ADD I K                      ; I = zy_next

        ; --- G. UPDATE Z-WAARDEN ---
        A -> L                       ; zx = zx_next
        I -> M                       ; zy = zy_next

        ; --- H. CHECK MAXIMALE DIEPTE ---
        INC Z                        ; iter++
        MAX_ITER -> B                ; B = 32
        IF (Z == B) TRUE {
            JMP MANDEL_DONE
        }

        JMP MANDEL_LOOP

    MANDEL_DONE:
        ; --- I. SCHRIJF RESULTAAT NAAR MAILBOX SLOT Y EN MARKER DONE (2) ---
        Z -> [mb_color + Y]          ; Sla iteratie-aantal op in slot Y
        2 -> A                       ; Status 2 = DONE
        A -> [mb_status + Y]         ; Vlag slot Y als DONE voor CPU 0
        AUTOCLOSE
}