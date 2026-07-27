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
; --- IF STATEMENT START (ID: 2) ---
    TSTE I, B
    JMPT __IF_END_2
; --- REPEAT LOOP START ---
__REP_START_1:
    CONTEXT I, SIEVE
    FAIL HARVEST_ONE
    INC I
    JOIN A, RETRY_SPAWN
RETRY_SPAWN:
    TSTE I, B
    JMPF __REP_START_1
; --- REPEAT LOOP END ---
__IF_END_2:
; --- IF STATEMENT END ---

DRAIN_LOOP:
    JOIN A, DRAIN_LOOP
    SYNC DRAIN_LOOP

DONE_LABEL:
    HALT

HARVEST_ONE:
    JOIN A, HARVEST_ONE
    JMP RETRY_SPAWN

SIEVE:
    LDI C, 0
    LDX A, 924
; --- IF STATEMENT START (ID: 3) ---
    TSTZ A
    JMPF __IF_END_3
    STX A, 924
    CLOSE
__IF_END_3:
; --- IF STATEMENT END ---
    LDI B, 1
; --- IF STATEMENT START (ID: 4) ---
    TSTE A, B
    JMPF __IF_END_4
    LDI A, 0
    STX A, 924
    CLOSE
__IF_END_4:
; --- IF STATEMENT END ---
    LDI B, 2
; --- IF STATEMENT START (ID: 5) ---
    TSTE A, B
    JMPF __IF_END_5
    STX A, 924
    CLOSE
__IF_END_5:
; --- IF STATEMENT END ---
    INC B
; --- IF STATEMENT START (ID: 6) ---
    TSTE A, B
    JMPF __IF_END_6
    STX A, 924
    CLOSE
__IF_END_6:
; --- IF STATEMENT END ---
    LDI B, 2

PRIME_LOOP:
    LD C, B
    MUL C, B
; --- IF STATEMENT START (ID: 8) ---
    TSTG C, A
    JMPF __IF_ELSE_8
    STX A, 924
    CLOSE
    JMP __IF_END_8
__IF_ELSE_8:
    LD C, A
    MOD C, B
; --- IF STATEMENT START (ID: 7) ---
    TSTZ C
    JMPF __IF_END_7
    STX C, 924
    CLOSE
__IF_END_7:
; --- IF STATEMENT END ---
__IF_END_8:
; --- IF STATEMENT END ---
    INC B
    JMP PRIME_LOOP