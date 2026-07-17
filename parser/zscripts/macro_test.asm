; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
; --- Start hygiënische macro: WAITING (ID: 1) ---
    LDI A, 10
__M1_LUS:
    DEC A
    TSTZ A
    JMPT __M1_LUS
; --- Einde macro: WAITING ---
; --- Start hygiënische macro: WAITING (ID: 2) ---
    LDI B, 20
__M2_LUS:
    DEC B
    TSTZ B
    JMPT __M2_LUS
; --- Einde macro: WAITING ---
    HALT