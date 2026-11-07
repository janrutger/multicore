; ==============================================================================
;  STERN-Z32 PLATFORM: ANDI (BITWISE AND IMMEDIATE) VERIFICATIE TEST
;  Doel: Test even/oneven checks en bitmasking met ANDI
; ==============================================================================

MAP {
     MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    SHARED RESULT_EVEN 1
    SHARED RESULT_ODD  1
    SHARED RESULT_MASK 1

    ; Definieer een herbruikbare macro voor pariteit of even-check
    MACRO even(dest, src) {
        LD dest, src      ; Kopieer veilig naar de bestemming
        ANDI dest, 1      ; Maskeer de LSB (dest is nu 0 als even, 1 als oneven)
    }

}

PROGRAM {
main:
    0 -> Z
    ; --- TEST 1: Even getal controleren (4 AND 1 -> verwachte uitkomst = 0) ---
    LDI A 4             ; Laad getal 4 (even) in register A
    even(Z, A)
    IF (Z ZERO) TRUE {
        STO Z RESULT_EVEN
    }

    ; --- TEST 2: Oneven getal controleren (7 AND 1 -> verwachte uitkomst = 1) ---
    LDI B 7             ; Laad getal 7 (oneven) in register B
    ANDI B 1            ; Maskeer bit 0 via ANDI
    STO B RESULT_ODD    ; Sla op in shared memory (verwacht: 1)

    ; --- TEST 3: Algemene bitmasking (92 AND 15 -> decimaal 0101 1100 AND 0000 1111) ---
    LDI C 92            ; Decimaal 92 (binair: 01011100)
    ANDI C 15           ; Filter de onderste 4 bits (nibble) eruit met masker 15
    STO C RESULT_MASK   ; Sla op in shared memory (verwacht: 12, want 1100 binair = 12)

    HALT                ; Einde simulatie
}