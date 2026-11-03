MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE ===
    CONST NUM_BODIES 12          ; Aantal deeltjes in de simulatie
    CONST MAX_STEPS 2500         ; Totaal aantal simulatieframes
    CONST CENTER_X 320000        ; Schermmidden X (320 * 1000 Q1000)
    CONST CENTER_Y 240000        ; Schermmidden Y (240 * 1000 Q1000)
    CONST FP_SCALE 1000          ; Q1000 Fixed-Point schaal
    CONST COLLISION_DIST 35000   ; r^2 drempelwaarde voor botsing/accretie

    ; === CIU COMMUNICATIE TAGS (PRODUCER-CONSUMER) ===
    CONST TAG_FRAME_START 200    ; Signaal van Sim-Master: Start van een nieuw frame
    CONST TAG_BODY_DATA   201    ; Payload: Lichaam ID, X, Y en Status voor weergave
    CONST TAG_FRAME_END   202    ; Signaal van Sim-Master: Frame compleet, scherm flushen
    CONST TAG_SIM_DONE    999    ; Signaal van Sim-Master: Simulatie volledig afgerond

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
; DOMEIN 1: CPU 0 (DISPLAY / RENDER SERVER - CONSUMER)
; Luistert non-blockingly naar de CIU-bus via event-polls.
; ==========================================================
main:
    0 -> A
    0 -> B
    0 -> C
    0 -> K
    0 -> X
    0 -> Y
    0 -> Z

    ; 1. Initialiseer GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Boot CPU 1 als de dedicated Simulatie Director (Remote Boot op CPU 1)
    1 -> A
    RBOOT A SIMULATION_DIRECTOR

; --- RENDER SERVER EVENT-LOOP (Non-blocking) ---
RENDER_LISTEN_LOOP:
    ; A. Ontvang TAG_FRAME_START (200): Maak scherm leeg en teken centrale zwarte gat
    TAG_FRAME_START -> B
    READ B () {
        

        CLR_CMD -> A
        OUT A CMD
        IOSYNC

        3 -> A                  ; Kleur 3 = blauw voor het centrale zwarte gat
        OUT A VAL
        CENTER_X -> A
        DIVI A, FP_SCALE
        OUT A X_POS
        CENTER_Y -> A
        DIVI A, FP_SCALE
        OUT A Y_POS
        PLOT_CMD -> A
        OUT A CMD
        IOSYNC
    }

    ; B. Verwerk ELK INDIVIDUEEL deeltje zodra het binnenkomt over de bus
    TAG_BODY_DATA -> K
    READ K (A, X, Y, Z) {
        ; A = deeltje ID, X = X-pos, Y = Y-pos, Z = status (1 = levend, -1 = dood)
        0 -> C
        IF (C > Z) TRUE {
            JMP _skip_server_plot   ; Dode deeltjes overslaan
        }

        12 -> C                     ; Kleur 12 voor levende deeltjes
        OUT C VAL

        X -> C
        DIVI C, FP_SCALE
        OUT C X_POS

        Y -> C
        DIVI C, FP_SCALE
        OUT C Y_POS

        PLOT_CMD -> C
        OUT C CMD                   
        IOSYNC

    _skip_server_plot:
    }

    ; C. Luister naar TAG_FRAME_END (202): Frame is compleet
    TAG_FRAME_END -> B
    READ B () {
        ; Frame volledig verwerkt     
    }

    ; D. Luister naar TAG_SIM_DONE (999): Sluit de render server af
    TAG_SIM_DONE -> B
    READ B () {
        HALT
    }

    JMP RENDER_LISTEN_LOOP

; ==========================================================
; DOMEIN 2: CPU 1 (SIMULATIE DIRECTOR / MASTER - PRODUCER)
; Beheert de initiële grid, de simulatieluiz en stuurt taken + berichten aan.
; ==========================================================
SIMULATION_DIRECTOR:
    0 -> A
    0 -> B 
    0 -> C
    0 -> I
    0 -> K
    0 -> L
    0 -> M
    0 -> X
    0 -> Y
    0 -> Z 
    NUM_BODIES -> B

    ; Initialiseer centrale zwarte gat massa op 0
    0 -> A
    A -> [central_m]

    ; --- DYNAMISCHE GRID BEREKENING OP BASIS VAN NUM_BODIES ---
    NUM_BODIES -> A
    16 -> Z
    IF (A > Z) TRUE {
        8 -> X          ; 8 kolommen voor grotere hoeveelheden
    } ELSE {
        4 -> X          ; 4 kolommen voor 16 deeltjes of minder
    }

    NUM_BODIES -> A
    X -> Z
    DIV A, Z            ; A = rows
    A -> Y              ; Y = rows

    X -> A
    SUBI A, 1
    12500 -> K
    MUL A, K
    A -> L              ; L = X-offset helft

    Y -> A
    SUBI A, 1
    12500 -> K
    MUL A, K
    A -> M              ; M = Y-offset helft

    ; 1. Initialiseer de deeltjes in een dynamisch berekend raster
    0 -> I
    REPEAT UNTIL (I == B) {
        1 -> Z
        Z -> [body_status_curr + I]
        Z -> [body_status_next + I]

        ; X-pos
        I -> A
        X -> C
        MOD A, C
        25000 -> K
        MUL A, K
        CENTER_X -> C
        SUB C, L
        ADD A, C
        A -> [body_x_curr + I]
        A -> [body_x_next + I]
        A -> B

        ; Y-pos
        I -> A
        X -> C
        DIV A, C
        25000 -> K
        MUL A, K
        CENTER_Y -> C
        SUB C, M
        ADD A, C
        A -> [body_y_curr + I]
        A -> [body_y_next + I]
        A -> C

        ; Rotatie-impuls
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

        2500 -> A
        A -> [body_m + I]

        INC I
        NUM_BODIES -> B
    }

    MAX_STEPS -> A
    A -> [step_counter]

; --- MASTER SIMULATIE LUS (PRODUCER) ---
SIMULATION_TICK:
    

    ; 2. Dispatch zwaartekracht/accretie taken naar worker-CPU's
    0 -> I
    NUM_BODIES -> B
    REPEAT UNTIL (I == B) {
        startTask(BODY_SIMULATE_accretion, I)
        INC I
        NUM_BODIES -> B
    }

    waitMatrix()

    ; 1. Stuur TAG_FRAME_START naar CPU 0 via CIU-bus
    TAG_FRAME_START -> B
    WRITE B ()

    ; 3. Buffer Swap en deeltjesdata doorsturen naar CPU 0 via CIU-bus
    0 -> M                       ; Gebruik M i.p.v. I als lussteller
    NUM_BODIES -> B
    SWAP_LOOP:
    [body_x_next + M] -> A
    A -> [body_x_curr + M]
    [body_y_next + M] -> A
    A -> [body_y_curr + M]
    [body_status_next + M] -> A
    A -> [body_status_curr + M]

    TAG_BODY_DATA -> B
    [body_x_curr + M] -> X
    [body_y_curr + M] -> Y
    [body_status_curr + M] -> Z
    WRITE B (M, X, Y, Z)     ; WRITE gebruikt I intern, maar M blijft veilig!

    INC M
    NUM_BODIES -> B
    IF (M == B) FALSE {
        JMP SWAP_LOOP
    }


    ; 4. Stuur TAG_FRAME_END naar CPU 0
    TAG_FRAME_END -> B
    WRITE B ()
    
    

    [step_counter] -> A
    DEC A
    A -> [step_counter]
    TSTZ A
    JMPF SIMULATION_TICK

    ; Simulatie klaar: stuur eindsignaal naar CPU 0
    TAG_SIM_DONE -> B
    WRITE B ()
    HALT


; ==========================================================
; DOMEIN 3: WORKER THREAD (ACCRETIE & ZWAARTEKRACHT ENGINE)
; Identiek aan de geoptimaliseerde berekeningslogica
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

    0 -> X
    0 -> Y

    [body_x_curr + M] -> B
    [body_y_curr + M] -> C

    0 -> L
    NUM_BODIES -> Z             
    REPEAT UNTIL (L == Z) {
        TSTE L, M
        JMPT _skip_self

        [body_status_curr + L] -> A
        0 -> Z                  
        IF (Z > A) TRUE {
            JMP _skip_self      
        }

        [body_x_curr + L] -> A  
        [body_y_curr + L] -> K  

        SUB A, B
        SUB K, C

        fmul_round(A, A, 1000, 500) 
        fmul_round(K, K, 1000, 500) 

        ADD A, K
        
        COLLISION_DIST -> Z     
        IF (Z > A) TRUE {
            IF (L > M) TRUE {
                -1 -> Z
                Z -> [body_status_next + L]
                
                [body_m + M] -> I       
                [body_m + L] -> K       
                ADD K, I                
                K -> Z

                [body_vx + M] -> A      
                [body_m + M] -> I       
                fmul_round(A, I, 1000, 500) 

                [body_vx + L] -> K      
                [body_m + L] -> I       
                fmul_round(K, I, 1000, 500) 

                ADD A, K                
                fdiv_round(A, Z, 1000, 500) 
                A -> [body_vx + M]

                [body_vy + M] -> A      
                [body_m + M] -> I       
                fmul_round(A, I, 1000, 500) 

                [body_vy + L] -> K      
                [body_m + L] -> I       
                fmul_round(K, I, 1000, 500) 

                ADD A, K                
                fdiv_round(A, Z, 1000, 500) 
                A -> [body_vy + M]

                [body_m + L] -> I
                [body_m + M] -> K
                ADD K, I
                K -> [body_m + M]
            }
        }

        ADDI A, 400
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

    [central_m] -> I
    0 -> Z
    IF (I > Z) TRUE {
        CENTER_X -> A
        SUB A, B
        A -> L

        CENTER_Y -> A
        SUB A, C
        A -> Z

        L -> A
        fmul_round(A, A, 1000, 500)

        Z -> K
        fmul_round(K, K, 1000, 500)

        ADD A, K
        ADDI A, 400
        A -> I

        L -> A
        [central_m] -> K
        fmul_round(A, K, 1000, 500)
        fdiv_round(A, I, 1000, 500)
        ADD X, A

        Z -> A
        [central_m] -> K
        fmul_round(A, K, 1000, 500)
        fdiv_round(A, I, 1000, 500)
        ADD Y, A
    }

    [body_vx + M] -> A
    [body_vy + M] -> K

    A -> I
    0 -> Z
    IF (I > Z) TRUE {
        fdivi(I, 30000, 1, 15000)
    } ELSE {
        fdivi(I, 30000, 1, -15000)
    }
    SUB A, I

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

    10000 -> Z
    IF (Z > B) TRUE {
        10000 -> B
        0 -> A
        A -> [body_vx + M]
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