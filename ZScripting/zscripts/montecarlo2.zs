MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE ===
    CONST TOTAL_ITERATIONS 4000000   ; 1.000.000 totaal
    CONST CHUNK_SIZE 5000            ; 1.000 iteraties per taakblok
    CONST TOTAL_CHUNKS 800          ; 1.000.000 / 10.000 = 100 blokken totaal
    ; CONST R_SQUARED 1073741849       ; 32767^2 (15-bit coördinaten)
    CONST R_SQUARED 4294836225       ; 65535^2 (16-bit coördinaten)
    
    CONST TAG_RESULT 100            ; Mailbox tag voor hit-resultaten
    CONST SCALE 4000                ; Q1000 schaalfactor

    ; I/O Poorten voor GraphicalDisplay
    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2
    CONST CLR_CMD 3

    ; === PRNG MACRO (Per context private SEED) ===
    PRIVATE SEED 1
    MACRO rand(val, size) {
        LDM val SEED
        RND32 val 21
        STO val SEED
        SHIFTR val size
    }

    ; === DYNAMISCHE TASK DISPATCHER (CIU & Lokaal) ===
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task       ; 1. Probeer remote worker via CIU netwerk
            SUCCES _spawnd
            CONTEXT arg task        ; 2. Probeer lokaal op CPU 0
            SUCCES _spawnd
            JMP _spawntask          ; Wacht tot er elders context-ruimte vrijkomt
        _spawnd:
    }
}

PROGRAM {

; ==========================================================
; DOMEIN 1: MASTER COORDINATOR (CPU 0 & DISPLAY PLOTTER)
; ==========================================================
main:
    0 -> A 
    0 -> B
    0 -> C                      ; C = Totale hit-teller accumulator
    0 -> K                      ; K = Aantal uitgestuurde chunks
    0 -> L                      ; L = Aantal binnengekomen voltooide chunks
    0 -> M 
    0 -> X 
    0 -> Y 
    0 -> Z

    ; Initialiseer de GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; Wis het scherm bij de start
    CLR_CMD -> A
    OUT A CMD
    IOSYNC

MASTER_DISPATCH_LOOP:
    TOTAL_CHUNKS -> Z
    IF (K == Z) TRUE {
        JMP MASTER_COLLECT_ONLY
    }

    K -> Y
    startTask(PI_CHUNK_WORKER, Y)
    INC K

MASTER_COLLECT_ONLY:
    TAG_RESULT -> B
    READ B (A) {
        ADD C, A                ; Tel binnengekomen hits op bij globale som
        INC L                   ; Chunk klaar! L++

        ; --- 1. BEREKEN ACTUELE TUSSENSTAND PI (Q1000) ---
        C -> X
        ; SCALE -> M
        MULI X, SCALE                ; X = Hits * SCALE

        L -> Y
        CHUNK_SIZE -> Z
        MUL Y, Z                ; Y = Totaal verwerkte iteraties tot nu toe
        DIV X, Y                ; X = Actuele Pi tussenstand

        ; --- 2. BEREKEN PIXEL X (0..639) ---
        L -> A
        639 -> B                ; Maximaal 639 i.p.v. 640 om overflow te voorkomen
        MUL A, B
        TOTAL_CHUNKS -> B
        DIV A, B                ; A = Pixel X op het scherm

        ; --- 3. BEREKEN PIXEL Y (0..479) ---
        SUBI X, 3100            ; Trek offset af (2500..3500 schaal)
        480 -> B
        MUL X, B
        80 -> B
        DIV X, B                ; Relatieve Y hoogte
        
        479 -> B
        SUB B, X                ; B = Inverteer Y voor schermcoördinaat

        ; --- 4. BEVEILIGING (CLAMPING BINNEN SCHERMGRENZEN) ---
        ; Check X max (639)
        640 -> Z
        IF (A > Z) TRUE {
            639 -> A
        }
        
        ; Check Y max (479)
        480 -> Z
        IF (B > Z) TRUE {
            479 -> B
        }
        
        ; Check Y min (0)
        0 -> Z
        IF (Z > B) TRUE {
            0 -> B
        }

        ; --- 5. PLOT STIP NAAR SCHERM ---
        12 -> Z                 ; Kleur 12
        OUT Z VAL
        OUT A X_POS             ; Veilige Pixel X
        OUT B Y_POS             ; Veilige Pixel Y

        PLOT_CMD -> Z
        OUT Z CMD
        IOSYNC
    }

    TOTAL_CHUNKS -> Z
    IF (L == Z) TRUE {
        JMP BENCHMARK_FINISHED
    }

    JMP MASTER_DISPATCH_LOOP

BENCHMARK_FINISHED:
    ; --- BEREKEN DEFINITIEVE PI DIRECT UIT HET TOTAAL ---
    C -> A                      ; A = Totale aantal hits
    SCALE -> B                  ; Vermenigvuldig met SCALE voor Q1000 schaal
    MUL A, B                    ; A = Hits * SCALE
    
    TOTAL_ITERATIONS -> B       ; Deel door het totale aantal iteraties
    B -> Z 
    DIVI Z 2
    ADD A Z
    DIV A, B                    ; A = (Hits * SCALE) / TOTAL_ITERATIONS

    A -> [1024]                 ; Adres 1024 = Berekende Pi x 1000 (bijv. 3141)
    C -> [1025]                 ; Adres 1025 = Totaal aantal hits
    HALT


; ==========================================================
; DOMEIN 2: ASYNCHRONE WORKER CONTEXT
; ==========================================================
PI_CHUNK_WORKER:
    [SEED] -> A
    IF (A ZERO) TRUE {
        CPUID A
        ; ADD A, Y
        ADDI A, 421
        STO A SEED
    }

    0 -> C                      ; C telt de hits in deze chunk
    ; 0 -> A
    0 -> B
    0 -> M

    CHUNK_SIZE -> X             ; Draai exact 10.000 iteraties

WORKER_LOOP:
    rand(A, 16)
    MUL A, A                    ; A = X^2

    rand(B, 16)
    MUL B, B                    ; B = Y^2

    ADD A, B                    ; A = X^2 + Y^2
    R_SQUARED -> M
    IF (A > M) FALSE {
        INC C                   ; Hits++
    }

    DEC X
    TSTZ X
    JMPF WORKER_LOOP

    TAG_RESULT -> B
    WRITE B (C)                 ; Stuur hits terug naar Master

    AUTOCLOSE
}