; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

MAIN:
; --- Start hygiënische macro: fill_list (ID: 1) ---
    LDI K, 49
    LDI I, 49
    ; --- REPEAT LOOP START ---
__REP_START_0:
    STX K, 974
    DEC K
    DEC I
    TSTZ I
    JMPF __REP_START_0
    ; --- REPEAT LOOP END ---
; --- Einde macro: fill_list ---
    LDI B, 49
    LDI I, 0

SPAWN_LOOP:
    TSTE I, B
    JMPT DRAIN_LOOP
    CONTEXT I, SIEF
    FAIL HARVEST_ONE
    INC I
    JMP SPAWN_LOOP

HARVEST_ONE:
    JOIN A, HARVEST_ONE
    JMP SPAWN_LOOP

DRAIN_LOOP:
    JOIN A, DRAIN_LOOP
    SYNC DONE_LABEL
    JMP DRAIN_LOOP

DONE_LABEL:
    HALT

SIEF:
    LDI K, 0
    LDI B, 1
    LDI C, 0
    LDX A, 974
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
    STX A, 974
    JMP end_sief

store_no_prime:
    LDI A, 0
    STX A, 974
    JMP end_sief

end_sief:
    CLOSE