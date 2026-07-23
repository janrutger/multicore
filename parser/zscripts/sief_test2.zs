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
        list_len -> B
        INC B
        0 -> I             ; Start-index voor het spawnen

    SPAWN_LOOP:
        TSTE I, B             ; Hebben we alle threads geprobeerd te starten?
        JMPT DRAIN_LOOP       ; Ja -> ga naar de afbouwfase

        ; Probeer een uCore te alloceren en start SIEVE met de huidige index I als context
        CONTEXT I, SIEVE
        FAIL HARVEST_ONE      ; Matrix vol (< 10 cores vrij)? Spring naar tijdelijk oogsten
        INC I                 ; Spawn is gelukt, ga naar de volgende index

        JOIN A SPAWN_LOOP     ; eerst een gready/early harvest
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
        SYNC DRAIN_LOOP       ; Spring naar drain_loop als er nog 'waiting'contexten zijn

    DONE_LABEL:
        HALT


    ; ==========================================================
    ;  DE SIEVE WORKER (Met decentrale schrijf-operatie)
    ; ==========================================================
    SIEVE:
        1 -> B
        0 -> C
        
        ; Register I bevat de unieke, lokale thread-index voor deze uCore
        ; LDX A, list_base      ; A = getal dat we gaan testen op prime
        [list_base + I] -> A

        TSTZ A 
        JMPT store_no_prime

        1 -> B 
        TSTE A, B
        JMPT store_no_prime

        INC B                   ; B = 2
        TSTE A, B
        JMPT store_prime

        INC B                   ; B = 3
        TSTE A, B
        JMPT store_prime

        2 -> B

    PRIME_LOOP:
        B -> C
        MUL C B
        
        TSTG C A
        JMPT store_prime

        A -> C
        MOD C, B

        TSTZ C
        JMPT store_no_prime

        INC B
        JMP PRIME_LOOP

    store_prime:
        ; Schrijf de priemwaarde (A) direct terug naar list_base + I (lokale index)
        A -> [list_base + I]
        JMP end_sief

    store_no_prime:
        ; Schrijf 0 terug naar list_base + I (lokale index)
        0 -> A 
        A -> [list_base + I]
        JMP end_sief

    end_sief:
        CLOSE                 ; Geef de uCore direct vrij voor de SPAWN_LOOP
}