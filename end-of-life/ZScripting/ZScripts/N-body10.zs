MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE ===
    CONST NUM_BODIES 12         ; 16 lichte deeltjes die op elkaar jagen
    CONST MAX_STEPS 2500        ; Aantal simulatieframes
    CONST CENTER_X 320000       ; Schermmidden X (320 * 1000 Q1000)
    CONST CENTER_Y 240000       ; Schermmidden Y (240 * 1000 Q1000)
    CONST FP_SCALE 1000         ; Q1000 Fixed-Point schaal
    CONST COLLISION_DIST 45000   ; r^2 drempelwaarde waarbij een botsing/accretie plaatsvindt

    ; === DOUBLE BUFFERING RAM ALLOCATIE (SHARED) ===
    SHARED body_x_curr 64       ; Read-only positie X huidig frame
    SHARED body_y_curr 64       ; Read-only positie Y huidig frame
    SHARED body_x_next 64       ; Write-only positie X volgend frame
    SHARED body_y_next 64       ; Write-only positie Y volgend frame

    SHARED body_vx 64           ; Snelheid X (Q1000)
    SHARED body_vy 64           ; Snelheid Y (Q1000)
    SHARED body_m  64           ; Massa per lichaam
    SHARED body_status_curr 64  ; 1 = Levend, -1 = Dood/Opgegeten (Huidig)
    SHARED body_status_next 64  ; 1 = Levend, -1 = Dood/Opgegeten (Volgend)

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
    NUM_BODIES -> B

    GRAPH_DEV -> A
    OUT A DEV

    ; 1. Initialiseer 16 lichte deeltjes in een wijde 4x4 MATRIX rond het centrum
    0 -> I
    REPEAT UNTIL (I == B) {
        ; Status op 1 (Levend) zetten
        1 -> Z
        Z -> [body_status_curr + I]
        Z -> [body_status_next + I]

        ; --- X-pos: Vergrote stapgrootte (25000) ---
        I -> A
        4 -> C
        MOD A, C            ; Kolom 0, 1, 2, 3
        25000 -> K          ; Tussenruimte vergroot naar 25.000
        MUL A, K            
        CENTER_X -> C
        SUBI C, 37500       ; Nieuwe helft van totaal (3 * 25000 / 2)
        ADD A, C            
        A -> [body_x_curr + I]
        A -> [body_x_next + I]
        A -> B              ; Bewaar X in B

        ; --- Y-pos: Vergrote stapgrootte (25000) ---
        I -> A
        4 -> C
        DIV A, C            ; Rij 0, 1, 2, 3
        25000 -> K          ; Tussenruimte vergroot naar 25.000
        MUL A, K            
        CENTER_Y -> C
        SUBI C, 37500       ; Nieuwe helft van totaal
        ADD A, C            
        A -> [body_y_curr + I]
        A -> [body_y_next + I]
        A -> C              ; Bewaar Y in C

        ; --- Rotatie-impuls iets opschalen voor de grotere baan ---
        ; Omdat ze verder van het centrum starten, mogen ze iets harder ronddraaien
        C -> A              
        CENTER_Y -> K
        SUB A, K            
        DIVI A, 6           ; Iets lossere/snellere deler (was 8)
        A -> [body_vx + I]

        B -> A              
        CENTER_X -> K
        SUB A, K            
        DIVI A, 6           
        MULI A, -1          
        A -> [body_vy + I]

        ; Standaard beginmassa
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

    ; Buffer Swap voor Posities, Massa's én Status (Levend/Dood)
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
    1 -> B
    MOD A, B
    TSTZ A
    JMPF SKIP_DRAW_SPAWN

    0 -> Z
    CONTEXT Z DRAW_WORKER

SKIP_DRAW_SPAWN:
    [step_counter] -> A
    DEC A
    A -> [step_counter]
    TSTZ A
    JMPF SIMULATION_TICK

    waitMatrix()
    HALT


; ==========================================================
; DOMEIN 2: ASYNCHRONE RENDER CONTEXT (Negeert dode deeltjes)
; ==========================================================
DRAW_WORKER:
    CLR_CMD -> A
    OUT A CMD
    IOSYNC

    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        ; Check of het deeltje nog leeft: 0 > status_curr betekent status = -1 (dood)
        [body_status_curr + I] -> A
        0 -> C
        IF (C > A) TRUE {
            JMP _skip_draw      ; Dode deeltjes worden overgeslagen
        }

        12 -> A                 ; Standaard kleur voor levende deeltjes
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
; DOMEIN 3: WORKER THREAD (ACCRETIE & MOMENTUM ENGINE)
; ==========================================================
BODY_SIMULATE_accretion:
    0 -> M
    I -> M                      

    ; 1. Check of ik zelf al dood ben in de CURR buffer (0 > status_curr)
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

    ; Anders: Ik leef nog! Zet alvast een veilige '1' klaar in next
    1 -> Z
    Z -> [body_status_next + M]

    0 -> X                      ; X-kracht accumulator
    0 -> Y                      ; Y-kracht accumulator

    ; Bewaar de huidige X en Y in veilige registers B en C
    [body_x_curr + M] -> B      ; B = Mijn X_curr
    [body_y_curr + M] -> C      ; C = Mijn Y_curr

    ; --- N-BODY & ACCRETIE INTERACTIE LUS ---
    0 -> L
    NUM_BODIES -> Z             
    REPEAT UNTIL (L == Z) {
        TSTE L M
        JMPT _skip_self

        ; Check of het andere deeltje L leeft (0 > status_curr)
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
                ; L wordt opgegeten door M!
                -1 -> Z
                Z -> [body_status_next + L]
                
                ; --- NATUURKUNDIG IMPULSBEHOUD (MOMENTUM) ---
                ; Bereken m_total = m_M + m_L en bewaar in register Z
                [body_m + M] -> I       ; I = m_M
                [body_m + L] -> K       ; K = m_L
                ADD K, I                ; K = m_total
                K -> Z                  ; Z = m_total (bewaar voor deling)

                ; 1. Nieuwe X-snelheid: (m_M * v_M_x + m_L * v_L_x) / m_total
                [body_vx + M] -> A      ; A = v_M_x
                [body_m + M] -> I       ; I = m_M
                fmul_round(A, I, 1000, 500) ; A = m_M * v_M_x

                [body_vx + L] -> K      ; K = v_L_x
                [body_m + L] -> I       ; I = m_L
                fmul_round(K, I, 1000, 500) ; K = m_L * v_L_x

                ADD A, K                ; A = Totale X-impuls
                fdiv_round(A, Z, 1000, 500) ; A = Nieuwe v_x

                ; --- INELASTISCHE DEMPING (Verlies 15% energie bij botsing) ---
                850 -> I                ; Factor 0.85 (behou 85% van snelheid)
                fmul_round(A, I, 1000, 500)
                A -> [body_vx + M]

                ; 2. Nieuwe Y-snelheid: (m_M * v_M_y + m_L * v_L_y) / m_total
                [body_vy + M] -> A      ; A = v_M_y
                [body_m + M] -> I       ; I = m_M
                fmul_round(A, I, 1000, 500) ; A = m_M * v_M_y

                [body_vy + L] -> K      ; K = v_L_y
                [body_m + L] -> I       ; I = m_L
                fmul_round(K, I, 1000, 500) ; K = m_L * v_L_y

                ADD A, K                ; A = Totale Y-impuls
                fdiv_round(A, Z, 1000, 500) ; A = Nieuwe v_y

                ; --- INELASTISCHE DEMPING voor Y ---
                850 -> I                
                fmul_round(A, I, 1000, 500)
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
        A -> Z                  ; Bewaar deler in Z

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

    ADD A, X                    ; VX_nieuw = VX + Fx
    ADD K, Y                    ; VY_nieuw = VY + Fy

    A -> [body_vx + M]
    K -> [body_vy + M]

    ; Bereken nieuwe positie op basis van veilige B (X) en C (Y)
    ADD B, A                    ; X_nieuw = B + VX
    ADD C, K                    ; Y_nieuw = C + VY

    ; Schermgrenzen Clamping
    10000 -> Z
    IF (Z > B) TRUE {
        10000 -> B
        0 -> A
        A -> [body_vx + M]
    }
    630000 -> Z
    IF (B > Z) TRUE {
        630000 -> B
        0 -> A
        A -> [body_vx + M]
    }

    10000 -> Z
    IF (Z > C) TRUE {
        10000 -> C
        0 -> K
        K -> [body_vy + M]
    }
    470000 -> Z
    IF (C > Z) TRUE {
        470000 -> C
        0 -> K
        K -> [body_vy + M]
    }

    B -> [body_x_next + M]
    C -> [body_y_next + M]

    AUTOCLOSE
}