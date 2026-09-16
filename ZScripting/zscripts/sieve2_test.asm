; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

MAIN:
    LDI A, 0
; --- Start hygiënische macro: fill_list (ID: 1) ---
    LDI K, 99
    LDI I, 99
    ; --- REPEAT LOOP START ---
__REP_START_0:
    STX K, 924
    DEC K
    DEC I
    TSTZ I
    JMPF __REP_START_0
    ; --- REPEAT LOOP END ---
; --- Einde macro: fill_list ---
    LDI B, 99
    INC B
    LDI I, 0
; --- START GEGENEREERDE SPAWN PIJPLIJN (ID: 1) ---
__SPAWN_1_LOOP:
    TSTE I, B
    JMPT __SPAWN_1_DRAIN
    CONTEXT I, SIEVE
    FAIL __SPAWN_1_FULL
    INC I
    JOIN A, __SPAWN_1_LOOP
    JMP __SPAWN_1_LOOP
__SPAWN_1_FULL:
    JOIN A, __SPAWN_1_FULL
    JMP __SPAWN_1_LOOP
__SPAWN_1_DRAIN:
    JOIN A, __SPAWN_1_DRAIN_WAIT
__SPAWN_1_DRAIN_WAIT:
    SYNC __SPAWN_1_DRAIN
__SPAWN_1_DONE:
; --- EINDE GEGENEREERDE SPAWN PIJPLIJN ---
    HALT

SIEVE:
    LDI C, 0
    LDX A, 924
; --- IF STATEMENT START (ID: 1) ---
    TSTZ A
    JMPF __IF_END_1
    STX A, 924
    CLOSE
__IF_END_1:
; --- IF STATEMENT END ---
    LDI B, 1
; --- IF STATEMENT START (ID: 2) ---
    TSTE A, B
    JMPF __IF_END_2
    LDI A, 0
    STX A, 924
    CLOSE
__IF_END_2:
; --- IF STATEMENT END ---
    LDI B, 2
; --- IF STATEMENT START (ID: 3) ---
    TSTE A, B
    JMPF __IF_END_3
    STX A, 924
    CLOSE
__IF_END_3:
; --- IF STATEMENT END ---
    INC B
; --- IF STATEMENT START (ID: 4) ---
    TSTE A, B
    JMPF __IF_END_4
    STX A, 924
    CLOSE
__IF_END_4:
; --- IF STATEMENT END ---
    LDI B, 2

PRIME_LOOP:
    LD C, B
    MUL C, B
; --- IF STATEMENT START (ID: 5) ---
    TSTG C, A
    JMPF __IF_END_5
    STX A, 924
    CLOSE
__IF_END_5:
; --- IF STATEMENT END ---
    LD C, A
    MOD C, B
; --- IF STATEMENT START (ID: 6) ---
    TSTZ C
    JMPF __IF_END_6
    STX C, 924
    CLOSE
__IF_END_6:
; --- IF STATEMENT END ---
    INC B
    JMP PRIME_LOOP