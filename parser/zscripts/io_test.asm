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
    LDI X, 0
    LDI Y, 0

LOOP:
    LD I, X
    LDX A, 1008
    TSTE A, B
    JMPT oogst_laatsten
    CONTEXT A, XOR_WORKER
    FAIL oogst
    INC X
    JOIN A, LOOP
    LD I, Y
    STX A, 992
    INC Y
    JMP LOOP

oogst:
    JOIN A, oogst
    LD I, Y
    STX A, 992
    INC Y
    JMP LOOP

oogst_laatsten:
    JOIN A, klaar
    LD I, Y
    STX A, 992
    INC Y
    JMP oogst_laatsten

klaar:
    SYNC oogst_laatsten
    LD I, Y
    STX B, 992

end_program:
    HALT

XOR_WORKER:
    LDI K, 13
    XOR A, K
    MUL K A
    MUL K A
    CLOSE