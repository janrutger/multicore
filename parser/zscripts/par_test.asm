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

; --- START GEGENEREERDE HARDWARE PARALLEL (Worker: XOR_WORKER, ID: 1) ---
__PIPE_1_LOOP:
    LD I, X
    LDX A, 1008
    TSTE A, B
    JMPT __PIPE_1_DRAIN
    CONTEXT A, XOR_WORKER
    FAIL __PIPE_1_HARVEST
    INC X
    JOIN A, __PIPE_1_LOOP
    LD I, Y
    STX A, 992
    INC Y
    JMP __PIPE_1_LOOP
__PIPE_1_HARVEST:
    JOIN A, __PIPE_1_HARVEST
    LD I, Y
    STX A, 992
    INC Y
    JMP __PIPE_1_LOOP
__PIPE_1_DRAIN:
    SYNC __PIPE_1_COLLECT
    JMP __PIPE_1_DONE
__PIPE_1_COLLECT:
    JOIN A, __PIPE_1_COLLECT
    LD I, Y
    STX A, 992
    INC Y
    JMP __PIPE_1_DRAIN
__PIPE_1_DONE:
    LD I, Y
    STX B, 992
    INC Y
; --- EINDE GEGENEREERDE HARDWARE PARALLEL ---

end_program:
    HALT

XOR_WORKER:
    LDI K, 7
    SM32_RND A, 7
    XOR A, K
    CLOSE