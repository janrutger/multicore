; ==============================================================================
;  STERN-Z32 PLATFORM: ATOMIC STATEMENT CONTEST TEST
; ==============================================================================

MAP {
     MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    SHARED MUTEX_LOCK 1       ; De gedeelde mutex
    SHARED SHARED_COUNTER 1   ; Gedeelde teller
    SHARED WORKER_LOG 1       ; Laatste schrijver log
    SHARED worker_retry 2     ; Retry tellers per worker
}

PROGRAM {
main:
    LDI A 1
    CONTEXT A CONCURRENT_WORKER   ; Lanceer Worker 1

    LDI A 2
    CONTEXT A CONCURRENT_WORKER   ; Lanceer Worker 2

WAIT_FOR_ALL:
    SYNC WAIT_FOR_ALL             ; Wacht tot alle workers klaar zijn
    HALT

CONCURRENT_WORKER:
    0 -> I

    ; --- HET NIEUWE ATOMIC BLOK REGELT DE LOCK/UNLOCK MECHANIEK AUTOMATISCH ---
    ATOMIC MUTEX_LOCK {
        LDM K SHARED_COUNTER
        INC K
        STO K SHARED_COUNTER

        STO A WORKER_LOG
        K -> [worker_retry + A]
    }

    AUTOCLOSE
}