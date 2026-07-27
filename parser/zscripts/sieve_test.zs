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
        0 -> A
        fill_list(list_base, list_len)
        list_len -> B
        INC B
        0 -> I             ; Start-index voor het spawnen

    ; ==========================================================
    ;  WHILE (I != B) LUS-STRUCTUUR (PRE-TEST)
    ; ==========================================================
    IF (I == B) FALSE {
        REPEAT UNTIL (I == B) {
            CONTEXT I, SIEVE
            FAIL HARVEST_ONE      ; Matrix vol? Spring naar verplicht oogsten
            INC I                 ; Spawn gelukt, volgende index

            ; JOIN A RETRY_SPAWN    ; Early greedy harvest
        RETRY_SPAWN:
        }
    }

    DRAIN_LOOP:
        ; Alle threads zijn gespawned. Wacht op de allerlaatste core.
        JOIN A DRAIN_LOOP
        SYNC DRAIN_LOOP

    DONE_LABEL:
        HALT

    HARVEST_ONE:
        ; De hardware-matrix zit vol. Wacht tot er 1 core vrijkomt.
        JOIN A, HARVEST_ONE
        JMP RETRY_SPAWN       ; Keer direct terug in de WHILE-lus



    ; ==========================================================
    ;  DE SIEVE WORKER (Met gestructureerde IF-logica)
    ; ==========================================================
    SIEVE:
        0 -> C

        ; Register I bevat de unieke, lokale thread-index voor deze uCore
        [list_base + I] -> A

        ; 1. Basisgevallen: 0 en 1 zijn GEEN priemgetallen
        IF (A ZERO) TRUE {
            A -> [list_base + I]        ; 'A' holds zero
            CLOSE
        }

        1 -> B
        IF (A == B) TRUE {
            0 -> A                      ; 'A' holds zero
            A -> [list_base + I]
            CLOSE
        }

        ; 2. Basisgevallen: 2 en 3 ZIJN priemgetallen
        2 -> B
        IF (A == B) TRUE {
            A -> [list_base + I]
            CLOSE
        }

        INC B                   ; B = 3
        IF (A == B) TRUE {
            A -> [list_base + I]
            CLOSE
        }

        ; 3. Delers testen vanaf B = 2
        2 -> B

    PRIME_LOOP:
        ; Test of B^2 > A (zo ja: A is gegarandeerd een priemgetal!)
        B -> C
        MUL C B
        IF (C > A) TRUE {
            A -> [list_base + I]
            CLOSE
        }

        ; Test of A deelbaar is door B (A % B == 0)
        A -> C
        MOD C, B
        IF (C ZERO) TRUE {
            C -> [list_base + I]                ; 'C' holds zero
            CLOSE
        }

        INC B
        JMP PRIME_LOOP
}