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
        0 -> I             ; Start-index voor het spawnen van workers

    ; ==========================================================
    ;  DE VOLLEDIGE PARALLELLE STREAMING PIJPLIJN
    ; ==========================================================
    SPAWN SIEVE I UNTIL (I == B) TRUE UPDATE {
        INC I              ; Wordt PAS geëxecuteerd na een geslaagde CONTEXT spawn!
    } HARVEST A {
        ; De worker-thread heeft zijn resultaat zelf al decentraal weggeschreven.
        ; Het HARVEST-blok bevrijdt hier enkel de uCore via dummy-register A.
    }

    HALT


    ; ==========================================================
    ;  DE SIEVE WORKER (Met gestructureerde IF-logica & Core-Besparing)
    ; ==========================================================
    SIEVE:
        0 -> C

        ; Register I bevat de unieke, lokale thread-index voor deze uCore
        [list_base + I] -> A

        ; 1. Basisgevallen: 0 en 1 zijn GEEN priemgetallen
        IF (A ZERO) TRUE {
            A -> [list_base + I]        ; 'A' bevat al 0
            CLOSE
        }

        1 -> B
        IF (A == B) TRUE {
            0 -> A                      ; Hergebruik 'A' als 0
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
            C -> [list_base + I]        ; 'C' bevat al 0 na de modulo (bespaart 1 uCore)
            CLOSE
        }

        INC B
        JMP PRIME_LOOP
}