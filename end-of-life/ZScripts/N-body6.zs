MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE ===
    CONST NUM_BODIES 16         ; 32 hemellichamen
    CONST MAX_STEPS 2500        ; Aantal simulatieframes
    CONST CENTER_X 320000       ; Schermmidden X (320 * 1000 Q1000)
    CONST CENTER_Y 240000       ; Schermmidden Y (240 * 1000 Q1000)
    CONST FP_SCALE 1000         ; Q1000 Fixed-Point schaal

    ; === DOUBLE BUFFERING RAM ALLOCATIE (SHARED) ===
    SHARED body_x_curr 32       ; Read-only positie X huidig frame
    SHARED body_y_curr 32       ; Read-only positie Y huidig frame
    SHARED body_x_next 32       ; Write-only positie X volgend frame
    SHARED body_y_next 32       ; Write-only positie Y volgend frame

    SHARED body_vx 32           ; Snelheid X (Q1000)
    SHARED body_vy 32           ; Snelheid Y (Q1000)
    SHARED body_m 32            ; Massa per lichaam

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
            RCONTEXT arg task   ; 1. Remote worker via CIU
            SUCCES _spawnd
            ; CONTEXT arg task    ; 2. Fallback lokaal op CPU 0
            ; SUCCES _spawnd
            JMP _spawntask      ; Wacht tot er een microcore vrijkomt
        _spawnd:
    }

    MACRO waitMatrix() {
        _waitMatrix:
        ALLSYNC _waitMatrix
    }
}

PROGRAM {

; ==========================================================
; DOMEIN 1: CPU 0 (MASTER COORDINATOR & DISPLAY MANAGER)
; ==========================================================
main:
    0 -> A
    0 -> I
    NUM_BODIES -> B             ; Laad 32 in register B voor veilige vergelijkingen!

    ; 1. Initialiseer GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Initialiseer beginposities, baansnelheden en massa's
    0 -> I
    REPEAT UNTIL (I == B) {
        ; TSTZ I
        IF (I ZERO) TRUE {
            ; Lichaam 0: Het centrale zware anker
            CENTER_X -> A
            A -> [body_x_curr + I]
            A -> [body_x_next + I]
            CENTER_Y -> A
            A -> [body_y_curr + I]
            A -> [body_y_next + I]
            0 -> A
            A -> [body_vx + I]
            A -> [body_vy + I]
            100000 -> A         ; Extra zware massa
            A -> [body_m + I]
        }
        IF (I ZERO) FALSE {
            ; Overige lichamen: Cirkelvormige spreiding rond centrum
            I -> A
            5 -> C
            MOD A, C            ; A = I % 5
            50000 -> C
            MUL A, C
            100000 -> C
            SUB A, C
            CENTER_X -> C
            ADD A, C            ; X_FP = CENTER_X + offset
            A -> [body_x_curr + I]
            A -> [body_x_next + I]

            I -> A
            7 -> C
            MOD A, C            ; A = I % 7
            40000 -> C
            MUL A, C
            120000 -> C
            SUB A, C
            CENTER_Y -> C
            ADD A, C            ; Y_FP = CENTER_Y + offset
            A -> [body_y_curr + I]
            A -> [body_y_next + I]

            ; Tangentiële start-impuls
            [body_y_curr + I] -> A
            CENTER_Y -> C
            SUB A, C            ; A = Y - CENTER_Y
            DIVI A, 10
            A -> [body_vx + I]

            [body_x_curr + I] -> A
            CENTER_X -> C
            SUB A, C            ; A = X - CENTER_X
            MULI A, -1
            DIVI A, 10
            A -> [body_vy + I]

            1000 -> A            ; Standaard massa
            A -> [body_m + I]
        }

        INC I
        NUM_BODIES -> B         ; Herstel B op 32
    }

    MAX_STEPS -> A
    A -> [step_counter]

; --- MASTER SIMULATIE LUS ---
SIMULATION_TICK:
    ; 1. Dispatch alle 32 zwaartekracht-taken naar de worker-CPU's
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

    ; 4. Lanceer DRAW_WORKER als asynchrone lokale context op CPU 0 (elke 3e stap)
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
        8 -> A                 ; Standaard kleur 12
        ; TSTZ I
        IF (I ZERO) TRUE {
            15 -> A             ; Heldere kleur 15 voor centrale ster
        }

        2 -> C
        IF (I == C) TRUE {
            5 -> A
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
        ; NUM_BODIES -> B
    }

    AUTOCLOSE                   ; Geef de lokale context op CPU 0 weer vrij

; ==========================================================
; DOMEIN 3: WORKER THREAD (DOUBLE-BUFFERED GRAVITY ENGINE)
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
    NUM_BODIES -> Z             ; Z = 32 voor vergelijking in REPEAT
    REPEAT UNTIL (L == Z) {
        TSTE L M
        JMPT _skip_self

        ; 1. Lees positie van Lichaam L uit CURRENT buffer
        [body_x_curr + L] -> A  ; A = X van lichaam L
        [body_y_curr + L] -> K  ; K = Y van lichaam L

        ; dx = X_l - X_i, dy = Y_l - Y_i
        SUB A, B                ; A = dx
        SUB K, C                ; K = dy

        ; Schaaf af voor kwadrateren om 32-bit overflow te voorkomen
        DIVI A, 100             ; A = dx_small
        DIVI K, 100             ; K = dy_small

        MUL A, A                ; dx_small^2
        MUL K, K                ; dy_small^2
        ADD A, K                ; r^2_small
        ADDI A, 200             ; Softening factor
        A -> K                  ; K = r^2_small (deler)

        ; X-as Kracht: (dx * Massa_l) / r^2
        [body_x_curr + L] -> A
        SUB A, B                ; A = dx (origineel)
        [body_m + L] -> I       ; I = Massa L
        MUL A, I
        DIV A, K
        DIVI A, 5              ; Schaalfactor
        ADD X, A                ; Accumuleer in X

        ; Y-as Kracht: (dy * Massa_l) / r^2
        [body_y_curr + L] -> A
        SUB A, C                ; A = dy (origineel)
        [body_m + L] -> I
        MUL A, I
        DIV A, K
        DIVI A, 5
        ADD Y, A                ; Accumuleer in Y

    _skip_self:
        INC L
        NUM_BODIES -> Z         ; Herstel Z op 32
    }

    ; Anker-check voor Lichaam 0 (Blijft vast op centrum staan)
    ; TSTZ M
    IF (M ZERO) TRUE {
        CENTER_X -> B
        CENTER_Y -> C
        B -> [body_x_next + M]
        C -> [body_y_next + M]
        AUTOCLOSE
    }

    ; Snelheids-update voor Lichaam 1 t/m 31
    [body_vx + M] -> A
    [body_vy + M] -> K

    ; DEMPING VIA SHIFT: Vervang trage DIVI 1024 door snelle bit-shift (>> 10) [cite: 1, 5]
    A -> I
    SHIFTR I 8                 ; I = A >> 10
    SUB A, I

    K -> I
    SHIFTR I 8                 ; I = K >> 10
    SUB K, I

    ADD A, X                    ; Nieuwe VX = oude VX + Fx
    ADD K, Y                    ; Nieuwe VY = oude VY + Fy

    A -> [body_vx + M]
    K -> [body_vy + M]

    ; Bereken nieuwe positie
    ADD B, A                    ; Nieuwe X = oude X + VX
    ADD C, K                    ; Nieuwe Y = oude Y + VY

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