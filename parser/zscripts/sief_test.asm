; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

MAIN:
; --- Start hygiënische macro: fill_list (ID: 1) ---
    LDI K, 90
    LDI I, 90
    ; --- REPEAT LOOP START ---
__REP_START_0:
    STX K, 924
    DEC K
    DEC I
    TSTZ I
    JMPF __REP_START_0
    ; --- REPEAT LOOP END ---
; --- Einde macro: fill_list ---
    LDI B, 90
    LDI I, 0
    LDI X, 0
    LDI Y, 0

; --- START GEGENEREERDE HARDWARE PARALLEL (Worker: SIEF, ID: 1) ---
__PIPE_1_LOOP:
    LD I, X
    LDX X, 924
    TSTE X, B
    JMPT __PIPE_1_DRAIN
    CONTEXT X, SIEF
    FAIL __PIPE_1_HARVEST
    INC X
    JOIN A, __PIPE_1_LOOP
    LD I, Y
    STX A, 924
    INC Y
    JMP __PIPE_1_LOOP
__PIPE_1_HARVEST:
    JOIN A, __PIPE_1_HARVEST
    LD I, Y
    STX A, 924
    INC Y
    JMP __PIPE_1_LOOP
__PIPE_1_DRAIN:
    SYNC __PIPE_1_COLLECT
    JMP __PIPE_1_DONE
__PIPE_1_COLLECT:
    JOIN A, __PIPE_1_COLLECT
    LD I, Y
    STX A, 924
    INC Y
    JMP __PIPE_1_DRAIN
__PIPE_1_DONE:
    LD I, Y
    STX B, 924
    INC Y
; --- EINDE GEGENEREERDE HARDWARE PARALLEL ---

    HALT

SIEF:
    LDI K, 0
    LDI B, 1
    LDI C, 0
    LD I, X
    LDX A, 924
    TSTZ A
    JMPT store_no_prime
    LDI B, 1
    TSTE A, B
    JMPT store_no_prime
    LDI B, 2
    TSTE A, B
    JMPT store_prime
    LDI B, 3
    TSTE A, B
    JMPT store_prime
    LDI B, 2

PRIME_LOOP:
    LDI K, 0
    ADD K, B
    MUL K, B
    TSTG K, A
    JMPT store_prime
    LDI C, 0
    ADD C, A
    MOD C, B
    TSTZ C
    JMPT store_no_prime
    INC B
    JMP PRIME_LOOP

store_prime:
    JMP end_sief

store_no_prime:
    LDI A, 0
    JMP end_sief

end_sief:
    CLOSE