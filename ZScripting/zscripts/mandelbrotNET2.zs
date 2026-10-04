MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & TAGS ===
    CONST IMG_WIDTH 200         ; 200 pixels breed
    CONST IMG_HEIGHT 200        ; 200 pixels hoog
    CONST WORKER_PIXELS 20000   ; 20.000 pixels per worker
    CONST WORKER_PIXELS_MIN1 19999

    CONST TAG_RESULT 100        ; Berichten-TAG "result" (Pixel data)
    CONST TAG_DONE   999        ; Berichten-TAG "done" (Worker klaar signaal)

    CONST MAX_ITER 32           ; Maximale Mandelbrot iteraties

    ; Fixed-Point Schaal (Q1000: 1000 = 1.000)
    CONST FP_SCALE 1000
    CONST FP_HALF 500
    CONST BAILOUT 4000          ; Ontsnappingsgrens |z|^2 > 4.0

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
}

PROGRAM {

; ==========================================================
; DOMEIN 1: CPU 0 (MASTER COORDINATOR & DISPLAY PLOTTER)
; Bootst Workers en sluit af zodra beide Workers TAG_DONE (999) sturen
; ==========================================================
main:
    0 -> A
    0 -> B
    0 -> C
    0 -> K
    0 -> L
    0 -> M                      ; Register M = Aantal voltooide Workers (0..2)
    0 -> X
    0 -> Y
    0 -> Z

    ; 1. Initialiseer GraphicalDisplay bus
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Boot Worker 1 (Link 0) voor Bovenste Helft
    1 -> A
    RBOOT A WORKER_TOP_ENTRY

    ; 3. Boot Worker 2 (Link 3) voor Onderste Helft
    3 -> A
    RBOOT A WORKER_BOTTOM_ENTRY

; --- MASTER LISTEN LOOP ---
MASTER_LISTEN_LOOP:
    ; A. Luister naar binnenkomende pixels (TAG 100)
    100 -> B
    READ B (A, X, Y) {
        MAX_ITER -> Z
        IF (A == Z) TRUE { 
            0 -> A
        }
        IF (A == Z) FALSE {
            MULI A 7
        }
        OUT A VAL

        X -> A
        MULI A 2
        OUT A X_POS

        Y -> A
        MULI A 2
        OUT A Y_POS

        PLOT_CMD -> A
        OUT A CMD
        IOSYNC
    }

    ; B. Luister naar Worker Completion Signalen (TAG 999)
    999 -> B
    READ B () {
        INC M                   ; Worker is klaar! M++
    }

    ; C. Check of beide Workers (2) hun DONE signaal hebben gestuurd
    2 -> K
    IF (M == K) TRUE {
        JMP MASTER_DONE
    }

    JMP MASTER_LISTEN_LOOP

MASTER_DONE:
    HALT


; ==========================================================
; DOMEIN 2 & 3: WORKER CPU'S (CPU 1 & CPU 4)
; ==========================================================
WORKER_TOP_ENTRY:
    0 -> L                      ; Start-pixel index = 0 (bovenste helft)
    JMP WORKER_START_JOB

WORKER_BOTTOM_ENTRY:
    20000 -> L                  ; Start-pixel index = 20000 (onderste helft)
    JMP WORKER_START_JOB

WORKER_START_JOB:
    0 -> A
    0 -> X
    0 -> Y
    0 -> M                      ; Register M = spawn_count = 0
    0 -> Z                      ; Register Z = recv_count = 0
    ; 0 -> K                      ; Register K = drain_timeout_counter = 0

; --- DISPATCH & FORWARD LUS (20.000 TAKEN) ---
WORKER_SPAWN_LOOP:
    WORKER_PIXELS -> C          ; C = 20000
    IF (M == C) TRUE {
        JMP WORKER_DRAIN_LOOP   ; Alle 20.000 contexten gestart
    }
    

    L -> A
    RCONTEXT A MANDEL_CALC      ; Upstream taakinjectie naar uCore
    SUCCES spawn_ok

    JMP CHECK_INCOMING_MSG

spawn_ok:
    INC L
    INC M

CHECK_INCOMING_MSG:
    100 -> B                    ; TAG_RESULT = 100
    READ B (A, X, Y) {
        100 -> B
        WRITE B (A, X, Y)       ; Stuur DIRECT door naar Parent CPU 0
        INC Z                   ; recv_count++
    }

    JMP WORKER_SPAWN_LOOP

; --- DRAIN LUS: Wacht tot resultaten doorgestuurd zijn (met Safety Timeout) ---
WORKER_DRAIN_LOOP:
    WORKER_PIXELS_MIN1 -> C          ; C = 20000
    IF (Z > C) TRUE {
        JMP WORKER_FINISH
    }

    ; Safety Timeout: als de worker 10.000 keer niks meer ontvangt, sluit af
    ; 10000 -> C
    ; IF (K == C) TRUE {
    ;     JMP WORKER_FINISH
    ; }

    100 -> B                    ; TAG_RESULT = 100
    READ B (A, X, Y) {
        100 -> B
        WRITE B (A, X, Y)
        INC Z
        ; 0 -> K                  ; Reset timeout teller bij ontvangen bericht
    }

    ; INC K                       ; Geen bericht ontvangen? Increment timeout teller
    JMP WORKER_DRAIN_LOOP

WORKER_FINISH:
    ; Stuur TAG_DONE (999) signaal zonder payload naar Parent CPU 0
    999 -> B
    WRITE B ()
    SUSPEND


; ==========================================================
; DOMEIN 4: uCore SUB-CONTEXT (PIXEL CALCULATION ENGINE)
; ==========================================================
MANDEL_CALC:
    0 -> I
    0 -> B
    0 -> C
    0 -> K
    0 -> L
    0 -> M
    0 -> X
    0 -> Y 
    0 -> Z 

    IMG_WIDTH -> Z              ; Z = 200
    
    A -> C
    MOD C Z

    A -> K
    DIV K Z

    C -> X
    K -> Y

    C -> A
    MULI A 14
    SUBI A 2000
    A -> C

    K -> A
    MULI A 14
    SUBI A 1400
    A -> K

    0 -> L
    0 -> M
    0 -> Z

MANDEL_CORE_LOOP:
    INC Z                       ; INC Z VOOROP: Iteratie 1 telt nu direct als Z = 1!

    L -> A
    fmul_round(A, L, FP_SCALE, FP_HALF)

    M -> B
    fmul_round(B, M, FP_SCALE, FP_HALF)

    A -> I
    ADD I B

    SUB A B
    ADD A C

    BAILOUT -> B
    IF (I > B) TRUE {
        JMP CALC_FINISHED
    }

    L -> I
    fmul_round(I, M, FP_SCALE, FP_HALF)
    MULI I 2
    ADD I K

    A -> L
    I -> M

    MAX_ITER -> B
    IF (Z == B) TRUE {
        JMP CALC_FINISHED
    }

    JMP MANDEL_CORE_LOOP

CALC_FINISHED:
    100 -> B
    WRITE B (Z, X, Y)
    AUTOCLOSE
}