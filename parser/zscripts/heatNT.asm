; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI I, 0
    LDI B, 0
    LDI M, 0
    LDI X, 0
    LDI Y, 0
    LDI I, 99
; --- REPEAT LOOP START ---
__REP_START_0:
    STX A, 2460
    STX A, 2360
    DEC I
    TSTZ I
    JMPF __REP_START_0
; --- REPEAT LOOP END ---
    LDI A, 70
    LDI I, 45
    STX A, 2460
    LDI Y, 30

SIMULATIE_STAP:
    LDI X, 0
    LDI B, 99
; --- START GEGENEREERDE SPAWN PIJPLIJN (ID: 1) ---
__SPAWN_1_LOOP:
    TSTE X, B
    JMPT __SPAWN_1_DRAIN
    CONTEXT X, HEAT_WORKER
    FAIL __SPAWN_1_FULL
    INC X
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
    LDI I, 0
    LDI I, 99
; --- REPEAT LOOP START ---
__REP_START_2:
    LDX C, 2360
; --- IF STATEMENT START (ID: 1) ---
    TSTZ C
    JMPT __IF_END_1
    LDI A, 2
    LDI B, 2
    OUT A, 0
    DIVI C, 5
    OUT C, 1
    LD M, I
    LDI A, 10
    MOD M, A
    MULI M, 10
    OUT M, 2
    LD M, I
    DIVI M, 10
    MULI M, 10
    OUT M, 3
    OUT B, 5
    IOSYNC
__IF_END_1:
; --- IF STATEMENT END ---
    DEC I
    TSTZ I
    JMPF __REP_START_2
; --- REPEAT LOOP END ---
    LDI I, 0
    LDI I, 99
; --- REPEAT LOOP START ---
__REP_START_3:
    LDX A, 2360
    STX A, 2460
    DEC I
    TSTZ I
    JMPF __REP_START_3
; --- REPEAT LOOP END ---
    DEC Y
    TSTZ Y
    JMPF SIMULATIE_STAP
    HALT

HEAT_WORKER:
    LDI A, 0
    LDI B, 0
    LDI I, 0
    LD A, X
    LDI B, 10
    MOD A, B
; --- IF STATEMENT START (ID: 4) ---
    TSTZ A
    JMPF __IF_END_4
    LD I, X
    STX A, 2360
    CLOSE
__IF_END_4:
; --- IF STATEMENT END ---
    LDI B, 9
; --- IF STATEMENT START (ID: 5) ---
    TSTE A, B
    JMPF __IF_END_5
    LDI A, 0
    LD I, X
    STX A, 2360
    CLOSE
__IF_END_5:
; --- IF STATEMENT END ---
    LDI B, 10
; --- IF STATEMENT START (ID: 6) ---
    TSTG B, X
    JMPF __IF_END_6
    LDI A, 0
    LD I, X
    STX A, 2360
    CLOSE
__IF_END_6:
; --- IF STATEMENT END ---
    LDI B, 89
; --- IF STATEMENT START (ID: 7) ---
    TSTG X, B
    JMPF __IF_END_7
    LDI A, 0
    LD I, X
    STX A, 2360
    CLOSE
__IF_END_7:
; --- IF STATEMENT END ---
    LDI B, 45
; --- IF STATEMENT START (ID: 8) ---
    TSTE X, B
    JMPF __IF_END_8
    LDI A, 70
    LD I, X
    STX A, 2360
    CLOSE
__IF_END_8:
; --- IF STATEMENT END ---
    LD A, X
    SUBI A, 10
    LD I, A
    LDX A, 2460
    LD B, X
    ADDI B, 10
    LD I, B
    LDX B, 2460
    ADD A, B
    LD B, X
    DEC B
    LD I, B
    LDX B, 2460
    ADD A, B
    LD B, X
    INC B
    LD I, B
    LDX B, 2460
    ADD A, B
    ADDI A, 3
    DIVI A, 4
    LD I, X
    STX A, 2360
    CLOSE