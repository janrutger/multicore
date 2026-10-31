MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE ===
    CONST NUM_BODIES 12          ; 16 lichte deeltjes die op elkaar jagen
    CONST MAX_STEPS 2500         ; Aantal simulatieframes
    CONST CENTER_X 320000        ; Schermmidden X (320 * 1000 Q1000)
    CONST CENTER_Y 240000        ; Schermmidden Y (240 * 1000 Q1000)
    CONST FP_SCALE 1000          ; Q1000 Fixed-Point schaal
    CONST COLLISION_DIST 35000   ; r^2 drempelwaarde voor botsing/accretie

    ; === DOUBLE BUFFERING RAM ALLOCATIE (SHARED) ===
    SHARED body_x_curr 64        ; Read-only positie X huidig frame
    SHARED body_y_curr 64        ; Read-only positie Y huidig frame
    SHARED body_x_next 64        ; Write-only positie X volgend frame
    SHARED body_y_next 64        ; Write-only positie Y volgend frame

    SHARED body_vx 64            ; Snelheid X (Q1000)
    SHARED body_vy 64            ; Snelheid Y (Q1000)
    SHARED body_m  64            ; Massa per lichaam
    SHARED body_status_curr 64   ; 1 = Levend, -1 = Dood/Opgegeten (Huidig)
    SHARED body_status_next 64   ; 1 = Levend, -1 = Dood/Opgegeten (Volgend)

    SHARED central_m 1           ; Massa van het centrale virtuele zwarte gat
    SHARED step_counter 1        ; Resterend aantal simulatieframes

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
            RCONTEXT arg task    ; Remote worker via CIU
            SUCCES _spawnd
            JMP _spawntask       ; Wacht tot er een microcore vrijkomt
        _spawnd:
    }

    MACRO waitMatrix() {
        _waitMatrix:
        ALLSYNC _waitMatrix
    }

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

    MACRO fmul_round(Rx, Ry, scale_val, half_val) {
        MUL Rx, Ry              
        ADDI Rx, half_val       
        DIVI Rx, scale_val      
    }
}

PROGRAM {

; ==========================================================
; DOMEIN 1: CPU 0 (MASTER COORDINATOR & DISPLAY MANAGER)
; ==========================================================
main:
    0 -> A
    0 -> C
    0 -> I
    0 -> K
    0 -> L
    0 -> M
    0 -> X
    0 -> Y
    0 -> Z 
    NUM_BODIES -> B

    GRAPH_DEV -> A
    OUT A DEV

    ; Initialiseer centrale zwarte gat massa op 0
    0 -> A
    A -> [central_m]

    ; --- DYNAMISCHE GRID BEREKENING OP BASIS VAN NUM_BODIES ---
    NUM_BODIES -> A
    16 -> Z
    IF (A > Z) TRUE {
        8 -> X          ; X = cols = 8 voor grotere hoeveelheden (bijv. 32 of 64)
    } ELSE {
        4 -> X          ; X = cols = 4 voor 16 deeltjes of minder
    }

    ; Bereken rijen: rows = NUM_BODIES / cols
    NUM_BODIES -> A
    X -> Z
    DIV A, Z            ; A = rows
    A -> Y              ; Y = rows

    ; Bereken X-offset helft: (cols - 1) * 12500 (omdat 25000 / 2 = 12500)
    X -> A              ; A = cols
    SUBI A, 1
    12500 -> K
    MUL A, K            ; A = X-offset helft
    A -> L              ; Bewaar X-offset helft in register L

    ; Bereken Y-offset helft: (rows - 1) * 12500
    Y -> A              ; A = rows
    SUBI A, 1
    12500 -> K
    MUL A, K            ; A = Y-offset helft
    A -> M              ; Bewaar Y-offset helft in register M

    ; 1. Initialiseer de deeltjes in een dynamisch berekend raster rond het centrum
    0 -> I
    REPEAT UNTIL (I == B) {
        ; Status op 1 (Levend) zetten
        1 -> Z
        Z -> [body_status_curr + I]
        Z -> [body_status_next + I]

        ; --- X-pos: Dynamische spreiding op basis van X (cols) en L (offset) ---
        I -> A
        X -> C              ; C = aantal kolommen
        MOD A, C            ; Kolom-index
        25000 -> K          
        MUL A, K            
        CENTER_X -> C
        SUB C, L            ; Trek de dynamische X-offset af van het centrum
        ADD A, C            
        A -> [body_x_curr + I]
        A -> [body_x_next + I]
        A -> B              ; Bewaar X tijdelijk in B

        ; --- Y-pos: Dynamische spreiding op basis van X (cols) en M (offset) ---
        I -> A
        X -> C              ; C = aantal kolommen (om rijen te bepalen via DIV)
        DIV A, C            ; Rij-index
        25000 -> K          
        MUL A, K            
        CENTER_Y -> C
        SUB C, M            ; Trek de dynamische Y-offset af van het centrum
        ADD A, C            
        A -> [body_y_curr + I]
        A -> [body_y_next + I]
        A -> C              ; Bewaar Y tijdelijk in C

        ; --- Rotatie-impuls ---
        C -> A              
        CENTER_Y -> K
        SUB A, K            
        DIVI A, 6           
        A -> [body_vx + I]

        B -> A              
        CENTER_X -> K
        SUB A, K            
        DIVI A, 6           
        MULI A, -1          
        A -> [body_vy + I]

        ; Standaard beginmassa (2500)
        2500 -> A           
        A -> [body_m + I]

        INC I
        NUM_BODIES -> B
    }

    MAX_STEPS -> A
    A -> [step_counter]

; --- MASTER SIMULATIE LUS ---
SIMULATION_TICK:
    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        startTask(BODY_SIMULATE_accretion, I)
        INC I
        NUM_BODIES -> B
    }

    waitMatrix()

    ; Buffer Swap voor Posities, Massa's én Status
    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        [body_x_next + I] -> A
        A -> [body_x_curr + I]
        [body_y_next + I] -> A
        A -> [body_y_curr + I]
        
        [body_status_next + I] -> A
        A -> [body_status_curr + I]
        
        INC I
        NUM_BODIES -> B
    }

    [step_counter] -> A
    ;1 -> B
    ;MOD A, B
    ;TSTZ A
    ;JMPF SKIP_DRAW_SPAWN

    0 -> Z
    CONTEXT Z DRAW_WORKER

; SKIP_DRAW_SPAWN:
    [step_counter] -> A
    DEC A
    A -> [step_counter]
    TSTZ A
    JMPF SIMULATION_TICK

    waitMatrix()
    HALT


; ==========================================================
; DOMEIN 2: ASYNCHRONE RENDER CONTEXT
; ==========================================================
DRAW_WORKER:
    ; korte sleep
    500 -> X 
    1 -> Y
    MOD X Y

    CLR_CMD -> A
    OUT A CMD
    IOSYNC

    ; --- TEKEN HET CENTRALE ZWARTE GAT (WIT, KLEUR 16) ---
    3 -> A                 ; Kleur 16 = Wit voor het centrum
    OUT A VAL

    CENTER_X -> A
    DIVI A, FP_SCALE        ; Schaal Q1000 naar schermpixels
    OUT A X_POS

    CENTER_Y -> A
    DIVI A, FP_SCALE        ; Schaal Q1000 naar schermpixels
    OUT A Y_POS

    PLOT_CMD -> A
    OUT A CMD
    IOSYNC

    ; --- TEKEN DE LEVENDE DEELTJES ---
    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        [body_status_curr + I] -> A
        0 -> C
        IF (C > A) TRUE {
            JMP _skip_draw      ; Sla dode deeltjes over
        }

        12 -> A                 ; Kleur voor levende deeltjes
        OUT A VAL

        [body_x_curr + I] -> A
        DIVI A, FP_SCALE
        OUT A X_POS

        [body_y_curr + I] -> A
        DIVI A, FP_SCALE
        OUT A Y_POS

        PLOT_CMD -> A
        OUT A CMD
        IOSYNC

    _skip_draw:
        INC I
        NUM_BODIES -> B
    }

    AUTOCLOSE


; ==========================================================
; DOMEIN 3: WORKER THREAD (ACCRETIE & ZWAARTEKRACHT ENGINE)
; ==========================================================
BODY_SIMULATE_accretion:
    0 -> M
    I -> M    

    0 -> A
    0 -> B
    0 -> C

    0 -> K 
    0 -> L 
    0 -> Z



    ; 1. Check of ik zelf al dood ben in de CURR buffer
    [body_status_curr + M] -> A
    0 -> C
    IF (C > A) TRUE {
        [body_x_curr + M] -> B
        [body_y_curr + M] -> C
        B -> [body_x_next + M]
        C -> [body_y_next + M]
        
        -1 -> Z
        Z -> [body_status_next + M]
        AUTOCLOSE
    }

    1 -> Z
    Z -> [body_status_next + M]

    0 -> X                      ; X-kracht accumulator
    0 -> Y                      ; Y-kracht accumulator

    [body_x_curr + M] -> B      ; B = Mijn X_curr
    [body_y_curr + M] -> C      ; C = Mijn Y_curr

    ; --- N-BODY & ACCRETIE INTERACTIE LUS ---
    0 -> L
    NUM_BODIES -> Z             
    REPEAT UNTIL (L == Z) {
        TSTE L M
        JMPT _skip_self

        [body_status_curr + L] -> A
        0 -> Z                  
        IF (Z > A) TRUE {
            JMP _skip_self      
        }

        [body_x_curr + L] -> A  
        [body_y_curr + L] -> K  

        SUB A, B                ; A = dx
        SUB K, C                ; K = dy

        fmul_round(A, A, 1000, 500) 
        fmul_round(K, K, 1000, 500) 

        ADD A, K                ; A = r^2_small
        
        ; === BOTSINGS-CHECK & IMPULSBEHOUD ===
        COLLISION_DIST -> Z     
        IF (Z > A) TRUE {
            IF (L > M) TRUE {
                -1 -> Z
                Z -> [body_status_next + L]
                
                ; --- NATUURKUNDIG IMPULSBEHOUD ---
                [body_m + M] -> I       
                [body_m + L] -> K       
                ADD K, I                
                K -> Z                  ; Z = m_total

                ; 1. Nieuwe X-snelheid
                [body_vx + M] -> A      
                [body_m + M] -> I       
                fmul_round(A, I, 1000, 500) 

                [body_vx + L] -> K      
                [body_m + L] -> I       
                fmul_round(K, I, 1000, 500) 

                ADD A, K                
                fdiv_round(A, Z, 1000, 500) 
                A -> [body_vx + M]

                ; 2. Nieuwe Y-snelheid
                [body_vy + M] -> A      
                [body_m + M] -> I       
                fmul_round(A, I, 1000, 500) 

                [body_vy + L] -> K      
                [body_m + L] -> I       
                fmul_round(K, I, 1000, 500) 

                ADD A, K                
                fdiv_round(A, Z, 1000, 500) 
                A -> [body_vy + M]

                ; 3. Massa optellen bij M
                [body_m + L] -> I
                [body_m + M] -> K
                ADD K, I
                K -> [body_m + M]
            }
        }
        ; ===================================

        ADDI A, 400             ; Softening factor
        A -> Z                  

        [body_x_curr + L] -> A
        SUB A, B                
        [body_m + L] -> I       
        
        fmul_round(A, I, 1000, 500)   
        fdiv_round(A, Z, 1000, 500)   
        ADD X, A                

        [body_y_curr + L] -> A
        SUB A, C                
        [body_m + L] -> I       
        
        fmul_round(A, I, 1000, 500)   
        fdiv_round(A, Z, 1000, 500)   
        ADD Y, A                

    _skip_self:
        INC L
        NUM_BODIES -> Z         
    }

    ; --- ZWAARTEKRACHT VAN HET CENTRALE ZWARTE GAT ---
    [central_m] -> I
    0 -> Z
    IF (I > Z) TRUE {
        ; 1. Bereken dx = CENTER_X - B
        CENTER_X -> A
        SUB A, B            ; A = dx
        A -> L              ; Bewaar dx in L

        ; 2. Bereken dy = CENTER_Y - C
        CENTER_Y -> A
        SUB A, C            ; A = dy
        A -> Z              ; Bewaar dy in Z

        ; 3. Bereken dx^2
        L -> A              ; A = dx
        fmul_round(A, A, 1000, 500) ; A = dx^2

        ; 4. Bereken dy^2
        Z -> K              ; K = dy (uit Z)
        fmul_round(K, K, 1000, 500) ; K = dy^2

        ; 5. r^2 = dx^2 + dy^2 + 400 (Softening)
        ADD A, K            ; A = r^2
        ADDI A, 400         ; A = r^2 + 400
        A -> I              ; Bewaar de veilige deler in register I

        ; --- X-kracht van het zwarte gat: (dx * central_m) / deler ---
        L -> A              ; A = dx (uit L)
        [central_m] -> K    ; K = central_m massa
        fmul_round(A, K, 1000, 500) ; A = dx * central_m
        fdiv_round(A, I, 1000, 500) ; A = (dx * central_m) / deler
        ADD X, A            ; Tel op bij X-kracht accumulator

        ; --- Y-kracht van het zwarte gat: (dy * central_m) / deler ---
        Z -> A              ; A = dy (uit Z)
        [central_m] -> K    ; K = central_m massa
        fmul_round(A, K, 1000, 500) ; A = dy * central_m
        fdiv_round(A, I, 1000, 500) ; A = (dy * central_m) / deler
        ADD Y, A            ; Tel op bij Y-kracht accumulator
    }

    ; --- SNELHEID & POSITIE UPDATE ---
    [body_vx + M] -> A
    [body_vy + M] -> K

    ; Demping VX
    A -> I
    0 -> Z
    IF (I > Z) TRUE {
        fdivi(I, 30000, 1, 15000)
    } ELSE {
        fdivi(I, 30000, 1, -15000)
    }
    SUB A, I

    ; Demping VY
    K -> I
    0 -> Z
    IF (I > Z) TRUE {
        fdivi(I, 30000, 1, 15000)
    } ELSE {
        fdivi(I, 30000, 1, -15000)
    }
    SUB K, I

    ADD A, X                    
    ADD K, Y                    

    A -> [body_vx + M]
    K -> [body_vy + M]

    ADD B, A                    
    ADD C, K                    

    ; Schermgrenzen Clamping & Zwarte Gat Voeding
    10000 -> Z
    IF (Z > B) TRUE {
        10000 -> B
        0 -> A
        A -> [body_vx + M]
        
        ; Voed het centrale zwarte gat bij wandbotsing!
        [central_m] -> A
        ADDI A, 3000
        A -> [central_m]
    }
    630000 -> Z
    IF (B > Z) TRUE {
        630000 -> B
        0 -> A
        A -> [body_vx + M]
        
        [central_m] -> A
        ADDI A, 3000
        A -> [central_m]
    }

    10000 -> Z
    IF (Z > C) TRUE {
        10000 -> C
        0 -> K
        K -> [body_vy + M]
        
        [central_m] -> A
        ADDI A, 3000
        A -> [central_m]
    }
    470000 -> Z
    IF (C > Z) TRUE {
        470000 -> C
        0 -> K
        K -> [body_vy + M]
        
        [central_m] -> A
        ADDI A, 3000
        A -> [central_m]
    }

    B -> [body_x_next + M]
    C -> [body_y_next + M]

    AUTOCLOSE
}