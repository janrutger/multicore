; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    STO A, 1023
    LDI A, 50
; --- REPEAT LOOP START ---
__REP_START_0:
spawn:
    CONTEXT A, WORKER
    FAIL spawn
    DEC A
    TSTZ A
    JMPF __REP_START_0
; --- REPEAT LOOP END ---

WORKER:
    LDM B, 1023
    ADD A, B
    STO A, 1023
    AUTOCLOSE