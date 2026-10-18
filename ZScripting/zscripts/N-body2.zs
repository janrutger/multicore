MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === GEHEUGEN ALLOCATIE (UNIVERSUM STATE) ===
    CONST NUM_BODIES 24        ; 24 hemellichamen
    SHARED body_x 24           ; Actuele X-posities (Q1000 Fixed-Point)
    SHARED body_y 24           ; Actuele Y-posities (Q1000 Fixed-Point)
    SHARED body_vx 24          ; Snelheid X (Q1000 Fixed-Point)
    SHARED body_vy 24          ; Snelheid Y (Q1000 Fixed-Point)

    SHARED step_counter 1      ; Simulatieframes
    CONST MAX_STEPS 500       ; Aantal simulatieframes

    ; Schermmidden (Q1000 Fixed-Point: 320 * 1000 = 320000)
    CONST CENTER_X 320000
    CONST CENTER_Y 240000

    ; Fixed-Point Schaal (Q1000)
    CONST FP_SCALE 1000
    CONST FP_HALF 500

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
            RCONTEXT arg task        ; Probeer remote worker via CIU
            SUCCES _spawnd
            CONTEXT arg task         ; Fallback: lokaal op CPU 0
            SUCCES _spawnd
            JMP _spawntask           ; Wacht tot er een core vrij komt
        _spawnd:
    }
}

PROGRAM {

; ==========================================================
; DOMEIN 1: CPU 0 (MASTER COORDINATOR & DISPLAY RENDERER)
; ==========================================================
main:
    0 -> A
    0 -> I
    0 -> B
    0 -> K

    ; 1. Initialiseer GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Initialiseer beginposities & tangentiale start-impuls (Q1000 Fixed-Point)
    0 -> I
    INIT_LOOP:
        ; --- FIXED-POINT X-POSITIE (320 +/- offset in FP) ---
        I -> A
        5 -> B
        MOD A, B           ; A = I % 5 (0..4)
        40000 -> B         ; 40 pixels offset in FP
        MUL A, B           ; A = (I % 5) * 40000
        80000 -> B         ; 80 pixels centrering offset in FP
        SUB A, B           ; Offset (-80.000 tot +80.000)
        CENTER_X -> B
        ADD A, B           ; X_FP = CENTER_X + offset
        A -> [body_x + I]  ; Sla FP-waarde op in Shared RAM

        ; --- FIXED-POINT Y-POSITIE (240 +/- offset in FP) ---
        I -> A
        7 -> B
        MOD A, B           ; A = I % 7 (0..6)
        30000 -> B         ; 30 pixels offset in FP
        MUL A, B
        90000 -> B         ; 90 pixels offset
        SUB A, B
        CENTER_Y -> B
        ADD A, B           ; Y_FP = CENTER_Y + offset
        A -> [body_y + I]  ; Sla FP-waarde op in Shared RAM

        ; --- TANGENTIELE START-IMPULS (OPTIE 1 in Fixed-Point) ---
        ; VX = -(Y_FP - CENTER_Y_FP) / 32
        [body_y + I] -> A
        CENTER_Y -> B
        SUB A, B           ; A = CENTER_Y - Y (in FP)
        DIVI A, 8         ; Milde, sub-pixel baansnelheid
        A -> [body_vx + I]

        ; VY = (X_FP - CENTER_X_FP) / 32
        [body_x + I] -> A
        CENTER_X -> B
        SUB A, B           ; A = X - CENTER_X (in FP)
        MULI A, -1
        DIVI A, 8
        A -> [body_vy + I]

        ; --- VOLGENDE LICHAAM ---
        INC I
        NUM_BODIES -> B
        IF (I == B) FALSE {
            JMP INIT_LOOP
        }

    MAX_STEPS -> A
    A -> [step_counter]

; --- MASTER RENDER & SIMULATIE STURINGSLUS ---
SIMULATION_TICK:
    0 -> I
    TICK_LOOP:
        startTask(BODY_SIMULATE_fp, I)

        INC I
        NUM_BODIES -> B
        IF (I == B) FALSE {
            JMP TICK_LOOP
        }

    WAIT_FOR_CONTEXTEN:
        ALLSYNC WAIT_FOR_CONTEXTEN

    ; --- FRAME THROTTLING VIA MODULO 3 OP STEP_COUNTER ---
    [step_counter] -> A
    3 -> B
    MOD A, B               ; A = step_counter % 3 (geeft 0, 1 of 2)
    TSTZ A                 ; Is de restwaarde 0? (dus elke 3e stap)
    JMPF SKIP_DRAWING      ; Zo nee, sla het renderen over!

    ; --- DISPLAY RENDEREN (1 op de 3 frames) ---
    CLR_CMD -> A 
    OUT A CMD
    IOSYNC

    0 -> I
    DRAW_LOOP:
        12 -> A
        OUT A VAL

        [body_x + I] -> A
        DIVI A, FP_SCALE   ; Fixed-Point -> Schermpixels
        OUT A X_POS

        [body_y + I] -> A
        DIVI A, FP_SCALE   ; Fixed-Point -> Schermpixels
        OUT A Y_POS

        PLOT_CMD -> A
        OUT A CMD
        IOSYNC

        INC I
        NUM_BODIES -> B
        IF (I == B) FALSE {
            JMP DRAW_LOOP
        }

SKIP_DRAWING:
    [step_counter] -> A
    DEC A
    A -> [step_counter]
    TSTZ A
    JMPF SIMULATION_TICK

    HALT

; ==========================================================
; DOMEIN 3: uCore SUB-CONTEXT (FIXED-POINT N-BODY ENGINE)
; Input: Register I bevat het Lichaam ID (0 t/m NUM_BODIES-1)
; ==========================================================
BODY_SIMULATE_fp:
    0 -> M
    I -> M                  ; M = mijn eigen Lichaam ID backup

    0 -> A 
    0 -> B 
    0 -> C 

    0 -> X                  ; Accumulator Delta VX (FP) = 0
    0 -> Y                  ; Accumulator Delta VY (FP) = 0
    0 -> L                  ; Inner-loop teller L = 0

    ; Lees eigen Fixed-Point positie
    LDX A, body_x           ; A = mijn X (FP)
    LDX K, body_y           ; K = mijn Y (FP)

    A -> B                  ; B = mijn X-backup (FP)
    K -> C                  ; C = mijn Y-backup (FP)

    NUM_BODIES -> Z         ; Z = 24

; --- N-BODY INTERACTIE LUS ---
N_BODY_LOOP:
    TSTE L M
    JMPT _skip_self

    [body_x + L] -> A       ; A = X van lichaam L (FP)
    [body_y + L] -> K       ; K = Y van lichaam L (FP)

    ; Bereken afstands-vector in Fixed-Point: dx = X_l - X_i
    SUB A, B                ; A = dx (FP)
    SUB K, C                ; K = dy (FP)

    ; Doordat we in FP rekenen, hebben we gigantische precisie!
    ; Zelfs bij kleine afstanden blijft de kracht keurig behouden.
    DIVI A, 500             ; Hoge precisie schaling
    DIVI K, 500

    ADD X, A                ; Accumuleer krachten
    ADD Y, K

_skip_self:
    INC L 
    TSTE L Z 
    JMPF N_BODY_LOOP 

    ; --- HERSTEL ID & UPDATE SNELHEDEN ---
    M -> I                  ; Herstel ID in I

    LDX A, body_vx         ; A = VX (FP)
    LDX K, body_vy         ; K = VY (FP)

    ; Zachte wrijving / energie-behoud in Fixed-Point: 
    ; In plaats van een harde SHIFTR 1 (50% verlies) trekken we slechts 2% af!
    A -> Z
    DIVI Z, 64
    SUB A, Z                ; VX = VX - (VX / 64)

    K -> Z
    DIVI Z, 64
    SUB K, Z                ; VY = VY - (VY / 64)

    ; Tel N-body krachten op
    ADD A, X 
    ADD K, Y 

    ; --- SCHERMCENTRUM ANKERKRACHT (FP PRECISIE) ---
    LDX B, body_x           ; B = Huidige X (FP)
    CENTER_X -> Z
    SUB Z, B                ; Z = CENTER_X_FP - X_FP
    DIVI Z, 128             ; Geen drempelfouten meer dankzij Q1000!
    ADD A, Z                ; Tel toe aan VX (FP)

    LDX C, body_y           ; C = Huidige Y (FP)
    CENTER_Y -> Z
    SUB Z, C
    DIVI Z, 128
    ADD K, Z                ; Tel toe aan VY (FP)

    ; Sla nieuwe Fixed-Point snelheden op
    STX A, body_vx
    STX K, body_vy

    ; --- UPDATE FIXED-POINT POSITIES ---
    ADD B, A                ; Nieuwe X (FP) = X (FP) + VX (FP)
    ADD C, K                ; Nieuwe Y (FP) = Y (FP) + VY (FP)

    STX B, body_x
    STX C, body_y

    AUTOCLOSE
}