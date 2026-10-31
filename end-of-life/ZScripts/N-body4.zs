MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === GEHEUGEN ALLOCATIE (UNIVERSUM STATE) ===
    CONST NUM_BODIES 36        ; 24 hemellichamen
    SHARED body_x 64           ; Actuele X-posities (Q1000 Fixed-Point)
    SHARED body_y 64           ; Actuele Y-posities (Q1000 Fixed-Point)
    SHARED body_vx 64          ; Snelheid X (Q1000 Fixed-Point)
    SHARED body_vy 64          ; Snelheid Y (Q1000 Fixed-Point)
    SHARED body_m 64           ; Massa per lichaam (Fixed-Point schaal)

    SHARED step_counter 1      ; Simulatieframes
    CONST MAX_STEPS 800        ; Aantal simulatieframes

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

    ; 2. Initialiseer beginposities, baansnelheden én massa's
    0 -> I
    INIT_LOOP:
        ; Check of dit Lichaam 0 is (de centrale zware ster)
        TSTZ I
        IF (I ZERO) TRUE {
            ; Lichaam 0 komt exact in het centrum en staat stil
            CENTER_X -> A
            A -> [body_x + I]
            CENTER_Y -> A
            A -> [body_y + I]
            0 -> A
            A -> [body_vx + I]
            A -> [body_vy + I]
            10000 -> A         ; Extra zware massa voor Lichaam 0
            A -> [body_m + I]
            JMP _init_next
        }

        ; --- VOOR DE OVERIGE LICHAMEN: Cirkelvormige spreiding rond het centrum ---
        I -> A
        5 -> B
        MOD A, B           ; A = I % 5 (0..4)
        50000 -> B         ; Grotere spreiding in FP
        MUL A, B           ; A = (I % 5) * 50000
        100000 -> B        
        SUB A, B           ; Offset
        CENTER_X -> B
        ADD A, B           ; X_FP = CENTER_X + offset
        A -> [body_x + I]

        I -> A
        7 -> B
        MOD A, B           ; A = I % 7 (0..6)
        40000 -> B         ; Spreiding in FP
        MUL A, B
        120000 -> B
        SUB A, B
        CENTER_Y -> B
        ADD A, B           ; Y_FP = CENTER_Y + offset
        A -> [body_y + I]

        ; --- TANGENTIELE START-IMPULS ---
        [body_y + I] -> A
        CENTER_Y -> B
        SUB A, B           ; A = Y - CENTER_Y
        DIVI A, 6          ; Baansnelheid X
        A -> [body_vx + I]

        [body_x + I] -> A
        CENTER_X -> B
        SUB A, B           ; A = X - CENTER_X
        MULI A, -1
        DIVI A, 6          ; Baansnelheid Y
        A -> [body_vy + I]

        ; --- STANDAARD MASSA VOOR REST ---
        1000 -> A
        A -> [body_m + I]

    _init_next:
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
    MOD A, B               ; A = step_counter % 3
    TSTZ A                 ; Restwaarde 0?
    JMPF SKIP_DRAWING      ; Zo nee, sla renderen over!

    ; --- DISPLAY RENDEREN ---
    CLR_CMD -> A 
    OUT A CMD
    IOSYNC

    0 -> I
    DRAW_LOOP:
        ; Kleur 15 (helder) voor Lichaam 0, Kleur 12 voor de rest
        12 -> A
        TSTZ I
        IF (I ZERO) TRUE {
            15 -> A        
        }
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
; DOMEIN 3: uCore SUB-CONTEXT (MASS-AWARE N-BODY ENGINE)
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

; --- MASSA-GEVOELIGE N-BODY INTERACTIE LUS ---
N_BODY_LOOP:
    TSTE L M
    JMPT _skip_self

    [body_x + L] -> A       ; A = X van lichaam L (FP)
    [body_y + L] -> K       ; K = Y van lichaam L (FP)

    ; Afstandsvector: dx = X_l - X_i
    SUB A, B                ; A = dx (FP)
    SUB K, C                ; K = dy (FP)

    ; --- MASSA EFFECT: Schaal de aantrekkingskracht met Massa van L ---
    [body_m + L] -> Z       ; Z = Massa van het aantrekkende lichaam L
    MUL A, Z                ; Force_X = dx * M_l
    MUL K, Z                ; Force_Y = dy * M_l

    DIVI A, 400000          ; Schaalfactor afgestemd op vrije massa's
    DIVI K, 400000

    ADD X, A                ; Accumuleer versnelling
    ADD Y, K

_skip_self:
    NUM_BODIES -> Z
    INC L 
    TSTE L Z 
    JMPF N_BODY_LOOP 

    ; --- HERSTEL ID & UPDATE SNELHEDEN ---
    M -> I                  ; Herstel ID in I

    ; --- CHECK OF DIT LICHAAM 0 IS ---
    TSTZ M
    IF (M ZERO) TRUE {
        ; Lichaam 0 deelt zijn massa en zwaartekracht uit via de lus hierboven,
        ; maar we dwingen de snelheid en positie vast op het centrum!
        CENTER_X -> B
        CENTER_Y -> C
        0 -> A
        0 -> K
        
        STX A, body_vx
        STX K, body_vy
        STX B, body_x
        STX C, body_y
        
        AUTOCLOSE
    }

    ; --- VOOR DE OVERIGE LICHAMEN (1 t/m 23): Normale update ---
    LDX A, body_vx          ; A = VX (FP)
    LDX K, body_vy          ; K = VY (FP)

    ; Lichte wrijving om banen te temmen
    A -> Z
    DIVI Z, 128
    SUB A, Z

    K -> Z
    DIVI Z, 128
    SUB K, Z

    ; Tel geaccumuleerde zwaartekracht op
    ADD A, X 
    ADD K, Y 

    ; Sla nieuwe Fixed-Point snelheden op
    STX A, body_vx
    STX K, body_vy

    ; --- UPDATE FIXED-POINT POSITIES ---
    ADD B, A                ; Nieuwe X (FP) = X + VX
    ADD C, K                ; Nieuwe Y (FP) = Y + VY

    STX B, body_x
    STX C, body_y

    AUTOCLOSE
}