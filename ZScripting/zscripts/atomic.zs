; ==============================================================================
;  STERN-Z32 PLATFORM: MULTI-WORKER LOCK CONTEST TEST
;  Doel: Twee threads vechten om dezelfde lock en meten de vertraging
; ==============================================================================

MAP {
     MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    SHARED MUTEX_LOCK 1       ; De gedeelde mutex (slot)
    SHARED SHARED_COUNTER 1   ; Gedeelde teller die beide workers willen ophogen
    SHARED WORKER_LOG 1       ; Om bij te houden wie er als laatst schreef
    SHARED worker_retry 2
}

PROGRAM {
main:
    ; --- STAP 1: LANCEER TWEE WORKERS TEGELIJK ---
    LDI A 1
    RCONTEXT A CONCURRENT_WORKER   ; Lanceer Worker 1

    LDI A 2
    RCONTEXT A CONCURRENT_WORKER   ; Lanceer Worker 2 (vecht om dezelfde lock!)

WAIT_FOR_ALL:
    ALLSYNC WAIT_FOR_ALL             ; Wacht tot beide workers klaar zijn
    HALT

; ==============================================================================
;  CONCURRERENDE WORKER ROUTINE
; ==============================================================================
CONCURRENT_WORKER:
    0 -> I
    ; Register X gebruiken we als lokale retry-teller (hoe vaak moesten we wachten?)
    LDI X 0

ACQUIRE_MUTEX:
    LOCK MUTEX_LOCK               ; Probeer de mutex te claimen
    SUCCES CRITICAL_SECTION       ; Gelukt? Ga naar de kritieke sectie
    
    INC X                         ; Niet gelukt: verhoog onze retry-teller
    JMP ACQUIRE_MUTEX             ; Spin-loop: probeer het direct opnieuw

CRITICAL_SECTION:
    ; --- KRITIEKE SECTIE: HIER KOMT MAAR 1 TEGELIJK IN ---
    
    ; Lees de huidige teller uit shared memory, verhoog hem, en schrijf terug
    ; (Dit simuleert een gedeelde resource waar normaliter race conditions ontstaan)
    LDM K SHARED_COUNTER
    INC K
    STO K SHARED_COUNTER

    ; Sla onze registerwaarde (ID van de worker) op in het log-adres
    STO A WORKER_LOG

    X -> [worker_retry + A]

    UNLOCK MUTEX_LOCK             ; Geef de mutex weer vrij voor de andere worker

    AUTOCLOSE                     ; Beëindig deze worker-thread
}