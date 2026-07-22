MAP {
    MEMSIZE 1024
    START MAIN

    RES list_base 100
    CONST list_len 90

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
        LDI B list_len

        LDI I 0
        LDI A 0
        LDI X 0         ; READ pointer
        LDI Y 0         ; WRITE pointer

        PARALLEL (SIEF) USING [list_base + X] UNTIL (A == B) {
        A -> [list_base + Y]
        INC Y
    }


    HALT

    ; ==========================================================
    ;  DE SIEF WORKER (Parallel ge ge ge ge-uitgevoerd op uCores)
    ; ==========================================================
    SIEF:
        LDI K 0
        LDI B 1
        LDI C 0
        

        A -> I
        ; I (R0) bevat de unieke index voor deze context
        LDX A list_base      ; A = getal dat we gaan testen op prime

        ; Check 1: Is A == 0? -> Geen prime
        TSTZ A 
        JMPT store_no_prime

        ; Check 2: Is A == 1? -> Geen prime
        LDI B 1
        TSTE A B
        JMPT store_no_prime

        ; Check 3: Is A == 2 of A == 3? -> Direct Prime!
        LDI B 2
        TSTE A B
        JMPT store_prime
        LDI B 3
        TSTE A B
        JMPT store_prime

        ; --- BEREKENINGSLUS VOOR PRIEMGETALLEN ---
        ; We delen A door deler B (startend vanaf B = 2)
        LDI B 2

    PRIME_LOOP:
        ; Stopconditie: als deler B * B > A, zijn we klaar en is A een PRIME!
        ; In plaats van een wortelberekening testen we: B * B > A
        ; Z32 Register-allocatie: K = B * B
        LDI K 0
        ADD K B              ; K = B
        MUL K B              ; K = B * B
        
        TSTG K A             ; Is (B * B) > A?
        JMPT store_prime     ; JA -> Alle mogelijke delers geprobeerd, het IS een prime!

        ; Test of A deelbaar is door B: C = A % B
        ; (Z32 MOD zet het resultaat van A % B in een uCore)
        LDI C 0
        ADD C A              ; Kopieer A naar C
        MOD C B              ; C = C % B

        ; Is de rest 0? Dan is A deelbaar door B, dus GEEN prime!
        TSTZ C
        JMPT store_no_prime

        ; Nog niet klaar? Increment deler B en ga door
        INC B
        JMP PRIME_LOOP


    store_prime:
        ; A bevat de oorspronkelijke prime-waarde. Schrijf A terug naar list_base + I
        JMP end_sief

    store_no_prime:
        ; Schrijf 0 terug naar list_base + I
        0 -> A
        JMP end_sief

    end_sief:
        CLOSE                ; Beëindig de hardware thread en geef uCore vrij
}