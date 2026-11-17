MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === GEHEUGEN ALLOCATIE (UNIVERSUM STATE) ===
    CONST NUM_BODIES 32        ; 24 hemellichamen
    SHARED body_x 64           ; Actuele X-posities (Q1000 Fixed-Point)
    SHARED body_y 64           ; Actuele Y-posities (Q1000 Fixed-Point)
    SHARED body_vx 64          ; Snelheid X (Q1000 Fixed-Point)
    SHARED body_vy 64          ; Snelheid Y (Q1000 Fixed-Point)
    SHARED body_m 64           ; Massa per lichaam (Fixed-Point schaal)

    SHARED step_counter 1      ; Simulatieframes
    CONST MAX_STEPS 1500        ; Aantal simulatieframes

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
            100000 -> A         ; Extra zware massa voor Lichaam 0
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
        DIVI A, 14          ; Baansnelheid X
        A -> [body_vx + I]

        [body_x + I] -> A
        CENTER_X -> B
        SUB A, B           ; A = X - CENTER_X
        MULI A, -1
        DIVI A, 14          ; Baansnelheid Y
        A -> [body_vy + I]

        ; --- STANDAARD MASSA VOOR REST ---
        500 -> A
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
        startTask(BODY_SIMULATE_mass, I)

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
; DOMEIN 3: uCore SUB-CONTEXT (OVERFLOW-SAFE GRAVITY ENGINE)
; ==========================================================
BODY_SIMULATE_mass:
    0 -> M
    I -> M                  ; M = mijn eigen Lichaam ID backup

    0 -> A 
    0 -> B 
    0 -> C 

    0 -> X                  ; Accumulator Delta VX (FP) = 0
    0 -> Y                  ; Accumulator Delta VY (FP) = 0
    0 -> L                  ; Inner-loop teller L = 0
    0 -> Z                  ; Veilig init

    ; Lees eigen Fixed-Point positie
    LDX A, body_x           ; A = mijn X (FP)
    LDX K, body_y           ; K = mijn Y (FP)

    A -> B                  ; B = mijn X-backup (FP)
    K -> C                  ; C = mijn Y-backup (FP)

    NUM_BODIES -> Z         ; Z = totaal aantal lichamen

; --- N-BODY INTERACTIE LUS ---
N_BODY_LOOP:
    TSTE L M
    JMPT _skip_self

    ; 1. Haal coördinaten van lichaam L op
    [body_x + L] -> A       ; A = X van lichaam L
    [body_y + L] -> K       ; K = Y van lichaam L

    ; dx = X_l - X_i, dy = Y_l - Y_i
    SUB A, B                ; A = dx
    SUB K, C                ; K = dy

    ; Bewaar originele dx voor de krachtberekening
    A -> Z                  ; Z = dx

    ; --- SCHAAL AF OM OVERFLOW TE VOORKOMEN BIJ KHWADRATEREN ---
    DIVI A, 100             ; A = dx_small
    DIVI K, 100             ; K = dy_small
    
    ; 2. Bereken r^2 met kleine waarden (geen overflow)
    MUL A, A                ; A = dx_small^2
    MUL K, K                ; K = dy_small^2
    ADD A, K                ; A = r^2_small
    
    ADDI A, 200             ; Kleinere softening factor voor schaal
    A -> K                  ; K = r^2_small (veilige deler)

    ; --- X-AS KRACHT: (dx * Massa) / r^2 ---
    Z -> A                  ; A = dx (origineel)
    [body_m + L] -> Z       ; Z = Massa van lichaam L
    MUL A, Z                ; A = dx * Massa_l
    DIV A, K                ; A = kracht X
    DIVI A, 20              ; Fijn afgestemde schaalfactor
    ADD X, A                ; Accumuleer in X

    ; --- Y-AS KRACHT: (dy * Massa) / r^2 ---
    [body_y + L] -> A       ; A = Y_l
    SUB A, C                ; A = dy (origineel)
    [body_m + L] -> Z       ; Z = Massa van lichaam L
    MUL A, Z                ; A = dy * Massa_l
    DIV A, K                ; A = kracht Y
    DIVI A, 20              ; Fijn afgestemde schaalfactor
    ADD Y, A                ; Accumuleer in Y

_skip_self:
    NUM_BODIES -> Z
    INC L 
    TSTE L Z 
    JMPF N_BODY_LOOP 

    ; --- HERSTEL ID ---
    M -> I                  ; Herstel ID in I

    ; --- CHECK OF DIT LICHAAM 0 IS (STATISCH ANKER) ---
    TSTZ M
    IF (M ZERO) TRUE {
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

    ; --- VOOR DE OVERIGE LICHAMEN (1 t/m N-1): Normale update ---
    LDX A, body_vx          ; A = VX (FP)
    LDX K, body_vy          ; K = VY (FP)

    ; Lichte wrijving om exploderende banen te dempen
    A -> Z
    DIVI Z, 1024           ; was 1024    
    SUB A, Z

    K -> Z
    DIVI Z, 1024            ; was 1024  
    SUB K, Z

    ; Tel geaccumuleerde zwaartekracht (X en Y) op bij de snelheid
    ADD A, X                ; A = nieuwe VX
    ADD K, Y                ; K = nieuwe VY

    ; Sla nieuwe snelheden op
    STX A, body_vx
    STX K, body_vy

    ; --- UPDATE FIXED-POINT POSITIES ---
    ADD B, A                ; Nieuwe X = oude X + nieuwe VX
    ADD C, K                ; Nieuwe Y = oude Y + nieuwe VY

    ; --- SCHERMGRENZEN CHECK (CLAMPING) ---
       ; X-as begrenzen tussen 10000 (rand links) en 630000 (rand rechts)
    10000 -> Z
    IF (Z > B) TRUE {
        10000 -> B
        ; MULI A, -1          ; Kaats snelheid om
        ; DIVI A, 2           ; Demp de klap
        0 -> A
    }
    630000 -> Z
    IF (B > Z) TRUE {
        630000 -> B
        ; MULI A, -1
        ; DIVI A, 2
        0 -> A
    }

       ; Y-as begrenzen tussen 10000 (rand boven) en 470000 (rand onder)
    10000 -> Z 
    IF (Z > C) TRUE {
        10000 -> C
        ; MULI K, -1
        ; DIVI K, 2
        0 -> K
    }
    470000 -> Z
    IF (C > Z) TRUE {
        470000 -> C
        ; MULI K, -1
        ; DIVI K, 2
        0 -> K
    }

    STX B, body_x
    STX C, body_y
    STX A, body_vx          ; Sla eventueel aangepaste snelheid op
    STX K, body_vy

    AUTOCLOSE
}