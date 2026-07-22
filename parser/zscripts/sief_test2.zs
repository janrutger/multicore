MAP {
    MEMSIZE 1024
    START MAIN

    RES list_base 100
    CONST list_len 99

    MACRO fill_list(base, len) {
        len -> K
        REPEAT I TIMES len {
            STX K base
            DEC K       
        }
    }
}

PROGRAM {
    MAIN:
        fill_list(list_base, list_len)
        ; LDI B, list_len
        list_len -> B
        INC B
        LDI I, 0              ; Start-index voor het spawnen

    SPAWN_LOOP:
        TSTE I, B             ; Hebben we alle 90 threads geprobeerd te starten?
        JMPT DRAIN_LOOP       ; Ja -> ga naar de afbouwfase

        ; Probeer een uCore te alloceren en start SIEF met de huidige index I als context
        CONTEXT I, SIEF
        FAIL HARVEST_ONE      ; Matrix vol (< 10 cores vrij)? Spring naar tijdelijk oogsten
        ; Spawn is gelukt, ga naar de volgende index
        INC I

        JOIN A SPAWN_LOOP       ; eerst een gready/early harvest
        JMP SPAWN_LOOP

    HARVEST_ONE:
        ; De hardware-matrix zit vol. We moeten wachten tot er minimaal één core vrijkomt.
        ; We doen een JOIN naar dummy-register A. Omdat de worker het resultaat zelf al
        ; heeft opgeslagen, negeren we de waarde in A. Het doel is enkel de core vrij te maken.
        JOIN A, HARVEST_ONE
        JMP SPAWN_LOOP        ; Er is weer een core vrij, probeer opnieuw te spawnen

    DRAIN_LOOP:
        ; Alle 90 threads zijn gespawned. We wachten nu tot de allerlaatste core klaar is.
        JOIN A DRAIN_LOOP
        ; SYNC DONE_LABEL
        ; JMP DRAIN_LOOP
        SYNC DRAIN_LOOP         ; Spring naar drain_loop als er nog 'waiting'contexten zijn

    DONE_LABEL:
        HALT


    ; ==========================================================
    ;  DE SIEF WORKER (Met decentrale schrijf-operatie)
    ; ==========================================================
    SIEF:
        ; LDI K, 0
        ; LDI B, 1
        1 -> B
        ; LDI C, 0
        0 -> C
        
        ; Register I bevat de unieke, lokale thread-index voor deze uCore
        ; LDX A, list_base      ; A = getal dat we gaan testen op prime
        [list_base + I] -> A

        TSTZ A 
        JMPT store_no_prime

        ; LDI B, 1
        1 -> B 
        TSTE A, B
        JMPT store_no_prime

        ; LDI B, 2
        INC B 
        TSTE A, B
        JMPT store_prime

        ; LDI B, 3
        INC B
        TSTE A, B
        JMPT store_prime

        ; LDI B, 2
        2 -> B

    PRIME_LOOP:
        ; LDI K, 0
        ; ADD K, B
        ; MUL K, B
        B -> C
        MUL C B
        
        ; TSTG K, A
        TSTG C A
        JMPT store_prime

        ; LDI C, 0
        ; ADD C, A
        A -> C
        MOD C, B

        TSTZ C
        JMPT store_no_prime

        INC B
        JMP PRIME_LOOP

    store_prime:
        ; Schrijf de priemwaarde (A) direct terug naar list_base + I (lokale index)
        ; STX A, list_base
        A -> [list_base + I]
        JMP end_sief

    store_no_prime:
        ; Schrijf 0 terug naar list_base + I (lokale index)
        ; LDI A, 0
        ; STX A, list_base
        0 -> A 
        A -> [list_base + I]
        JMP end_sief

    end_sief:
        CLOSE                 ; Geef de uCore direct vrij voor de SPAWN_LOOP
}