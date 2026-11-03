MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE ===
    CONST NUM_BODIES 12         ; 2 zware sterren + 6 or more vrije elementen
    CONST MAX_STEPS 2500        ; Aantal simulatieframes
    CONST CENTER_X 320000       ; Schermmidden X (320 * 1000 Q1000)
    CONST CENTER_Y 240000       ; Schermmidden Y (240 * 1000 Q1000)
    CONST FP_SCALE 1000         ; Q1000 Fixed-Point schaal

    ; === DOUBLE BUFFERING RAM ALLOCATIE (SHARED) ===
    SHARED body_x_curr 64       ; Read-only positie X huidig frame
    SHARED body_y_curr 64       ; Read-only positie Y huidig frame
    SHARED body_x_next 64       ; Write-only positie X volgend frame
    SHARED body_y_next 64       ; Write-only positie Y volgend frame

    SHARED body_vx 64           ; Snelheid X (Q1000)
    SHARED body_vy 64           ; Snelheid Y (Q1000)
    SHARED body_m  64           ; Massa per lichaam

    SHARED step_counter 1       ; Resterend aantal simulatieframes

    ; I/O Poorten voor GraphicalDisplay
    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2
    CONST CLR_CMD 3

    ; === MACRO'S ===
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task   ; Remote worker via CIU
            SUCCES _spawnd
            JMP _spawntask      ; Wacht tot er een microcore vrijkomt
        _spawnd:
    }

    MACRO waitMatrix() {
        _waitMatrix:
        ALLSYNC _waitMatrix
    }

    ; MACRO fdiv(Rx, denominator, scale_val, half_val)
    ; Berekent: Rx = ((Rx * scale_val) + half_val) / denominator
    MACRO fdiv_round(Rx, denominator, scale_val, half_val) {
        MULI Rx, scale_val
        ADDI Rx, half_val
        DIV Rx, denominator
    }
    
    MACRO fdivi(Rx, denominator, scale_val, half_val) {
        MULI Rx, scale_val
        ADDI Rx, half_val
        DIVI Rx, denominator
    }

    ; MACRO fmul_round(Rx, Ry, scale_val, half_val)
    ; Berekent: Rx = (Rx * Ry + half_val) / scale_val
    MACRO fmul_round(Rx, Ry, scale_val, half_val) {
        MUL Rx, Ry              ; Vermenigvuldig de twee Q1000 getallen (wordt Q1000^2)
        ADDI Rx, half_val       ; Voeg afrondingshelft toe voor de decimale precisie
        DIVI Rx, scale_val      ; Deel terug naar de standaard Q1000 schaal
    }
}

PROGRAM {

; ==========================================================
; DOMEIN 1: CPU 0 (MASTER COORDINATOR & DISPLAY MANAGER)
; ==========================================================
main:
    0 -> A
    0 -> I
    NUM_BODIES -> B             ; B = 8

    ; 1. Initialiseer GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Initialiseer de Dubbelster en de vrije elementen
    0 -> I
    REPEAT UNTIL (I == B) {
        
        ; --- STER 0 (Zware primaire ster - Links van centrum) ---
        IF (I ZERO) TRUE {
            CENTER_X -> A
            SUBI A 40000        ; X = CENTER_X - 40.000
            A -> [body_x_curr + I]
            A -> [body_x_next + I]

            CENTER_Y -> A
            A -> [body_y_curr + I]
            A -> [body_y_next + I]

            0 -> A
            A -> [body_vx + I]
            -9000 -> A           ; Snelheid omhoog (+Y)
            A -> [body_vy + I]

            200000 -> A         ; Zware massa voor Ster 0
            A -> [body_m + I]
        }

        ; --- STER 1 (Zware secundaire ster - Rechts van centrum) ---
        1 -> C
        IF (I == C) TRUE {
            CENTER_X -> A
            ADDI A 40000        ; X = CENTER_X + 40.000
            A -> [body_x_curr + I]
            A -> [body_x_next + I]

            CENTER_Y -> A
            A -> [body_y_curr + I]
            A -> [body_y_next + I]

            0 -> A
            A -> [body_vx + I]
            9000 -> A          ; Snelheid omlaag (-Y, tegengesteld aan Ster 0)
            A -> [body_vy + I]

            200000 -> A         ; Zware massa voor Ster 1
            A -> [body_m + I]
        }

        ; --- VRIJE ELEMENTEN (Lichamen 2 t/m 11) ---
        IF (I ZERO) FALSE {
            IF (I == C) FALSE {
                ; 1. Symmetrische X-verdeling rond CENTER_X (-60.000 tot +60.000)
                I -> A
                5 -> C
                MOD A, C            ; A = I % 5 (0..4)
                30000 -> C
                MUL A, C            ; 0, 30000, 60000, 90000, 120000
                60000 -> C
                SUB A, C            ; -60000, -30000, 0, 30000, 60000
                CENTER_X -> C
                ADD A, C            ; X_FP
                A -> [body_x_curr + I]
                A -> [body_x_next + I]

                ; 2. Symmetrische Y-verdeling rond CENTER_Y (-90.000 tot +90.000)
                I -> A
                7 -> C
                MOD A, C            ; A = I % 7 (0..6)
                30000 -> C
                MUL A, C            ; 0 t/m 180000
                90000 -> C          ; Aangepast naar 90000 voor exacte symmetrie!
                SUB A, C            ; -90000 t/m +90000
                CENTER_Y -> C
                ADD A, C            ; Y_FP
                A -> [body_y_curr + I]
                A -> [body_y_next + I]

                ; 3. Tangentiële start-impuls AANGEPAST AAN SCHERM-Y
                [body_y_curr + I] -> A
                CENTER_Y -> C
                SUB A, C            ; A = Y - CENTER_Y
                DIVI A, 10
                A -> [body_vx + I]

                [body_x_curr + I] -> A
                CENTER_X -> C
                SUB A, C            ; A = X - CENTER_X
                DIVI A, 10          ; GEEN MULI A, -1 meer! Scherm-Y gecorrigeerd.
                A -> [body_vy + I]

                4000 -> A           ; Lichte massa
                A -> [body_m + I]
            }
        }

        INC I
        NUM_BODIES -> B         ; Herstel B op 8
    }

    MAX_STEPS -> A
    A -> [step_counter]

; --- MASTER SIMULATIE LUS ---
SIMULATION_TICK:
    ; 1. Dispatch zwaartekracht-taken naar de worker-CPU's
    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        startTask(BODY_SIMULATE_mass, I)
        INC I
        NUM_BODIES -> B
    }

    ; 2. Wacht totdat ALLE worker-CPU's klaar zijn met schrijven in 'next'
    waitMatrix()

    ; 3. Buffer Swap (Kopieer 'next' naar 'curr')
    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        [body_x_next + I] -> A
        A -> [body_x_curr + I]
        [body_y_next + I] -> A
        A -> [body_y_curr + I]
        INC I
        NUM_BODIES -> B
    }

    ; 4. Lanceer DRAW_WORKER als asynchrone lokale context op CPU 0
    [step_counter] -> A
    1 -> B
    MOD A, B
    TSTZ A
    JMPF SKIP_DRAW_SPAWN

    0 -> Z
    CONTEXT Z DRAW_WORKER       ; Tekenen draait asynchroon op de achtergrond!

SKIP_DRAW_SPAWN:
    [step_counter] -> A
    DEC A
    A -> [step_counter]
    TSTZ A
    JMPF SIMULATION_TICK

    waitMatrix()                ; Laatste flush voor HALT
    HALT

; ==========================================================
; DOMEIN 2: ASYNCHRONE LOKALE RENDER CONTEXT (CPU 0)
; ==========================================================
DRAW_WORKER:
    CLR_CMD -> A
    OUT A CMD
    IOSYNC

    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        3 -> A                 ; Standaard kleur 12 (Paars/Blauw)

        IF (I ZERO) TRUE {
            15 -> A             ; Kleur 15 (Wit/Geel) voor Ster 0
        }

        1 -> C
        IF (I == C) TRUE {
            14 -> A             ; Kleur 14 (Oranje/Rood) voor Ster 1
        }

        OUT A VAL

        [body_x_curr + I] -> A
        DIVI A, FP_SCALE        ; Fixed-Point -> Schermpixel
        OUT A X_POS

        [body_y_curr + I] -> A
        DIVI A, FP_SCALE        ; Fixed-Point -> Schermpixel
        OUT A Y_POS

        PLOT_CMD -> A
        OUT A CMD
        IOSYNC

        INC I
        NUM_BODIES -> B
    }

    AUTOCLOSE                   ; Geef de lokale context op CPU 0 weer vrij

; ==========================================================
; DOMEIN 3: WORKER THREAD (DOUBLE-BUFFERED PRECISION GRAVITY ENGINE)
; ==========================================================
BODY_SIMULATE_mass:
    0 -> M
    I -> M                      ; Sla eigen Lichaam ID op in M

    0 -> X                      ; Accumulator Delta VX = 0
    0 -> Y                      ; Accumulator Delta VY = 0

    ; Lees eigen positie uit de STABIELE READ-ONLY CURRENT buffer
    [body_x_curr + M] -> B      ; B = Mijn X_curr
    [body_y_curr + M] -> C      ; C = Mijn Y_curr

; --- N-BODY INTERACTIE LUS ---
    0 -> L
    NUM_BODIES -> Z             ; Z = 12 voor vergelijking in REPEAT
    REPEAT UNTIL (L == Z) {
        TSTE L M
        JMPT _skip_self

        ; 1. Lees positie van Lichaam L uit CURRENT buffer
        [body_x_curr + L] -> A  ; A = X van lichaam L
        [body_y_curr + L] -> K  ; K = Y van lichaam L

        ; dx = X_l - X_i, dy = Y_l - Y_i
        SUB A, B                ; A = dx
        SUB K, C                ; K = dy

        ; Kwadrateren met Q1000 Fixed-Point precisie
        fmul_round(A, A, 1000, 500) ; A = dx_small^2 in Q1000
        fmul_round(K, K, 1000, 500) ; K = dy_small^2 in Q1000

        ADD A, K                ; A = r^2_small
        ADDI A, 400             ; Softening factor (0.4 in Q1000)
        A -> K                  ; K = r^2_small (deler in Q1000)

        ; --- X-AS KRACHT (VOLLEDIG Q1000 GESCHAALD) ---
        [body_x_curr + L] -> A
        SUB A, B                ; A = dx (origineel Q1000)
        [body_m + L] -> I       ; I = Massa L (Q1000)
        
        fmul_round(A, I, 1000, 500)   ; A = dx * Massa (teruggebracht naar Q1000)
        fdiv_round(A, K, 1000, 500)   ; A = (dx * Massa) / K (teruggebracht naar Q1000)
        
        ADD X, A                ; Accumuleer in X

        ; --- Y-AS KRACHT (VOLLEDIG Q1000 GESCHAALD) ---
        [body_y_curr + L] -> A
        SUB A, C                ; A = dy (origineel Q1000)
        [body_m + L] -> I       ; I = Massa L (Q1000)
        
        fmul_round(A, I, 1000, 500)   ; A = dy * Massa (teruggebracht naar Q1000)
        fdiv_round(A, K, 1000, 500)   ; A = (dy * Massa) / K (teruggebracht naar Q1000)
        
        ADD Y, A                ; Accumuleer in Y

    _skip_self:
        INC L
        NUM_BODIES -> Z         ; Herstel Z op 12
    }

    ; --- TEKEN-BEWUSTE DEMPING & POSITIE UPDATE ---
    [body_vx + M] -> A
    [body_vy + M] -> K

    ; Symmetrische demping op VX (deler = 2048, half_val = 1024)
    A -> I
    IF (I > 0) TRUE {
        fdivi(I, 3000, 1, 1500)
    } ELSE {
        fdivi(I, 3000, 1, -1500)
    }
    SUB A, I

    ; Symmetrische demping op VY (deler = 2048, half_val = 1024)
    K -> I
    IF (I > 0) TRUE {
        fdivi(I, 3000, 1, 1500)
    } ELSE {
        fdivi(I, 3000, 1, -1500)
    }
    SUB K, I

    ADD A, X                    ; VX_nieuw = VX + Fx
    ADD K, Y                    ; VY_nieuw = VY + Fy

    A -> [body_vx + M]
    K -> [body_vy + M]

    ; Bereken nieuwe positie
    ADD B, A                    ; X_nieuw = X + VX
    ADD C, K                    ; Y_nieuw = Y + VY

    ; Schermgrenzen Clamping
    10000 -> I
    IF (I > B) TRUE {
        10000 -> B
        0 -> A
        A -> [body_vx + M]
    }
    630000 -> I
    IF (B > I) TRUE {
        630000 -> B
        0 -> A
        A -> [body_vx + M]
    }

    10000 -> I
    IF (I > C) TRUE {
        10000 -> C
        0 -> K
        K -> [body_vy + M]
    }
    470000 -> I
    IF (C > I) TRUE {
        470000 -> C
        0 -> K
        K -> [body_vy + M]
    }

    ; Schrijf de berekende positie naar de WRITE-ONLY NEXT buffer
    B -> [body_x_next + M]
    C -> [body_y_next + M]

    AUTOCLOSE
}