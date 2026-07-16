; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI I, 5
; --- REPEAT LOOP START ---
__REP_START_0:
    INC A
    DEC I
    TSTZ I
    JMPF __REP_START_0
; --- REPEAT LOOP END ---
    LDI K, 10
; --- REPEAT LOOP START ---
__REP_START_1:
    INC A
    TSTE A, K
    JMPF __REP_START_1
; --- REPEAT LOOP END ---
    TSTG A, K
    LDI B, 0
    LDI K, 1
    LDI K, 10
; --- REPEAT LOOP START ---
__REP_START_2:
    IN B, 2
    INC A
    TSTE B, K
    JMPT __REP_END_2
    DEC K
    TSTZ K
    JMPF __REP_START_2
__REP_END_2:
; --- REPEAT LOOP END ---
    STO A, 1007
    HALT