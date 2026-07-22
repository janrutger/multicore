; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

MAIN:
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

SPAWN_LOOP:
    TSTE I, B
    JMPT DRAIN_LOOP
    CONTEXT I, SIEF
    FAIL HARVEST_ONE
    INC I
    JOIN A, SPAWN_LOOP
    JMP SPAWN_LOOP

HARVEST_ONE:
    JOIN A, HARVEST_ONE
    JMP SPAWN_LOOP

DRAIN_LOOP:
    JOIN A, DRAIN_LOOP
    SYNC DRAIN_LOOP

DONE_LABEL:
    HALT

SIEF:
    LDI B, 1
    LDI C, 0
    LDX A, 924
    TSTZ A
    JMPT store_no_prime
    LDI B, 1
    TSTE A, B
    JMPT store_no_prime
    INC B
    TSTE A, B
    JMPT store_prime
    INC B
    TSTE A, B
    JMPT store_prime
    LDI B, 2

PRIME_LOOP:
    LD C, B
    MUL C, B
    TSTG C, A
    JMPT store_prime
    LD C, A
    MOD C, B
    TSTZ C
    JMPT store_no_prime
    INC B
    JMP PRIME_LOOP

store_prime:
    STX A, 924
    JMP end_sief

store_no_prime:
    LDI A, 0
    STX A, 924
    JMP end_sief

end_sief:
    CLOSE