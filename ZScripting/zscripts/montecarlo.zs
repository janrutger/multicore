MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === CONSTANTEN & CONFIGURATIE (400k RUN) ===
    CONST TOTAL_ITERATIONS 1000000   ; 400.000 totaal
    CONST CHUNK_SIZE 10000          ; 10.000 iteraties per taakblok
    CONST TOTAL_CHUNKS 100           ; 400.000 / 10.000 = 40 blokken totaal
    CONST R_SQUARED 1073741849      ; 32767^2 (15-bit coördinaten)
    
    CONST TAG_RESULT 100            ; Mailbox tag voor hit-resultaten

    CONST SCALE 4000

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
; DOMEIN 1: MASTER COORDINATOR (CPU 0 - Register Zuinig)
; ==========================================================
main:
    0 -> C                      ; C = Totale hit-teller accumulator
    0 -> K                      ; K = Aantal uitgestuurde chunks (0..TOTAL_CHUNKS)
    0 -> L                      ; L = Aantal binnengekomen voltooide chunks (0..TOTAL_CHUNKS)
    0 -> Y 
    0 -> Z

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
    }

    TOTAL_CHUNKS -> Z
    IF (L == Z) TRUE {
        JMP BENCHMARK_FINISHED
    }

    JMP MASTER_DISPATCH_LOOP

BENCHMARK_FINISHED:
    ; --- BEREKEN DEFINITIEVE PI DIRECT UT HET TOTAAL ---
    C -> A                      ; A = Totale aantal hits
    SCALE -> B                  ; Vermenigvuldig met SCALE voor Q1000 schaal
    MUL A, B                    ; A = Hits * SCALE
    
    TOTAL_ITERATIONS -> B       ; Deel door het totale aantal iteraties
    DIV A, B                    ; A = (Hits * SCALE) / TOTAL_ITERATIONS

    A -> [1024]                 ; Adres 1024 = Berekende Pi x 1000
    C -> [1025]                 ; Adres 1025 = Totaal aantal hits
    HALT


; ==========================================================
; DOMEIN 2: ASYNCHRONE WORKER CONTEXT
; ==========================================================
PI_CHUNK_WORKER:
    CPUID A
    ADDI A, 421
    STO A SEED

    0 -> C                      ; C telt de hits in deze chunk
    0 -> A
    0 -> B
    0 -> M
    ; 0 -> X
    ; 0 -> Y
    ; 0 -> Z

    CHUNK_SIZE -> X             ; Draai exact 10.000 iteraties

WORKER_LOOP:
    rand(A, 17)
    LD M, A
    MUL A, M                    ; A = X^2

    rand(B, 17)
    LD M, B
    MUL B, M                    ; B = Y^2

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