; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI I, 0
    LDI B, 27
; --- REPEAT LOOP START ---
__REP_START_0:
; --- Start hygiënische macro: KBDread (ID: 1) ---
__M1_POLL_LUS:
    IOSYNC
    IN A, 6
    LDI K, 0
    TSTZ A
    JMPT __M1_POLL_LUS
; --- Einde macro: KBDread ---
    STX A, 1008
    INC I
; --- Start hygiënische macro: PRTchar (ID: 2) ---
    LDI K, 1
    LDI L, 1
    OUT K, 0
    OUT A, 1
    OUT L, 5
    IOSYNC
; --- Einde macro: PRTchar ---
    TSTE A, B
    JMPF __REP_START_0
; --- REPEAT LOOP END ---

end_program:
    HALT