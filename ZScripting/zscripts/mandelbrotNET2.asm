; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI B, 0
    LDI C, 0
    LDI K, 0
    LDI L, 0
    LDI M, 0
    LDI X, 0
    LDI Y, 0
    LDI Z, 0
    LDI A, 2
    OUT A, 0
    LDI A, 0
    RBOOT A, WORKER_TOP_ENTRY
    LDI A, 3
    RBOOT A, WORKER_BOTTOM_ENTRY

MASTER_LISTEN_LOOP:
    LDI B, 100
    MSG_PROBE B
    FAIL _SKIP_READ_1
    MSG_OPEN I
    MSG_READ I, A
    MSG_READ I, X
    MSG_READ I, Y
    MSG_CLOSE I
        LDI Z, 32
        ; --- IF STATEMENT START (ID: 0) ---
    TSTE A, Z
    JMPF __IF_END_0
    LDI A, 0
__IF_END_0:
; --- IF STATEMENT END ---
        ; --- IF STATEMENT START (ID: 1) ---
    TSTE A, Z
    JMPT __IF_END_1
    MULI A, 7
__IF_END_1:
; --- IF STATEMENT END ---
        OUT A, 1
        LD A, X
        MULI A, 2
        OUT A, 2
        LD A, Y
        MULI A, 2
        OUT A, 3
        LDI A, 2
        OUT A, 5
        IOSYNC
_SKIP_READ_1:
    LDI B, 999
    MSG_PROBE B
    FAIL _SKIP_READ_2
    MSG_OPEN I
    MSG_CLOSE I
        INC M
_SKIP_READ_2:
    LDI K, 2
; --- IF STATEMENT START (ID: 2) ---
    TSTE M, K
    JMPF __IF_END_2
    JMP MASTER_DONE
__IF_END_2:
; --- IF STATEMENT END ---
    JMP MASTER_LISTEN_LOOP

MASTER_DONE:
    HALT

WORKER_TOP_ENTRY:
    LDI L, 0
    JMP WORKER_START_JOB

WORKER_BOTTOM_ENTRY:
    LDI L, 20000
    JMP WORKER_START_JOB

WORKER_START_JOB:
    LDI A, 0
    LDI X, 0
    LDI Y, 0
    LDI M, 0
    LDI Z, 0

WORKER_SPAWN_LOOP:
    LDI C, 20000
; --- IF STATEMENT START (ID: 3) ---
    TSTE M, C
    JMPF __IF_END_3
    JMP WORKER_DRAIN_LOOP
__IF_END_3:
; --- IF STATEMENT END ---
    LD A, L
    RCONTEXT A, MANDEL_CALC
    SUCCES spawn_ok
    CONTEXT A, MANDEL_CALC
    SUCCES spawn_ok
    JMP CHECK_INCOMING_MSG

spawn_ok:
    INC L
    INC M

CHECK_INCOMING_MSG:
    LDI B, 100
    MSG_PROBE B
    FAIL _SKIP_READ_3
    MSG_OPEN I
    MSG_READ I, A
    MSG_READ I, X
    MSG_READ I, Y
    MSG_CLOSE I
        LDI B, 100
        LDI I, 3
    MSG_START B, I
    MSG_WRITE I, A
    MSG_WRITE I, X
    MSG_WRITE I, Y
    MSG_DONE I
        INC Z
_SKIP_READ_3:
    JMP WORKER_SPAWN_LOOP

WORKER_DRAIN_LOOP:
    LDI C, 19999
; --- IF STATEMENT START (ID: 4) ---
    TSTG Z, C
    JMPF __IF_END_4
    JMP WORKER_FINISH
__IF_END_4:
; --- IF STATEMENT END ---
    LDI B, 100
    MSG_PROBE B
    FAIL _SKIP_READ_4
    MSG_OPEN I
    MSG_READ I, A
    MSG_READ I, X
    MSG_READ I, Y
    MSG_CLOSE I
        LDI B, 100
        LDI I, 3
    MSG_START B, I
    MSG_WRITE I, A
    MSG_WRITE I, X
    MSG_WRITE I, Y
    MSG_DONE I
        INC Z
_SKIP_READ_4:
    JMP WORKER_DRAIN_LOOP

WORKER_FINISH:
    LDI B, 999
    LDI I, 0
    MSG_START B, I
    MSG_DONE I
    SUSPEND

MANDEL_CALC:
    LDI I, 0
    LDI B, 0
    LDI C, 0
    LDI K, 0
    LDI L, 0
    LDI M, 0
    LDI X, 0
    LDI Y, 0
    LDI Z, 0
    LDI Z, 200
    LD C, A
    MOD C, Z
    LD K, A
    DIV K, Z
    LD X, C
    LD Y, K
    LD A, C
    MULI A, 14
    SUBI A, 2000
    LD C, A
    LD A, K
    MULI A, 14
    SUBI A, 1400
    LD K, A
    LDI L, 0
    LDI M, 0
    LDI Z, 0

MANDEL_CORE_LOOP:
    INC Z
    LD A, L
; --- Start hygiënische macro: fmul_round (ID: 1) ---
    MUL A, L
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD B, M
; --- Start hygiënische macro: fmul_round (ID: 2) ---
    MUL B, M
    ADDI B, 500
    DIVI B, 1000
; --- Einde macro: fmul_round ---
    LD I, A
    ADD I, B
    SUB A, B
    ADD A, C
    LDI B, 4000
; --- IF STATEMENT START (ID: 5) ---
    TSTG I, B
    JMPF __IF_END_5
    JMP CALC_FINISHED
__IF_END_5:
; --- IF STATEMENT END ---
    LD I, L
; --- Start hygiënische macro: fmul_round (ID: 3) ---
    MUL I, M
    ADDI I, 500
    DIVI I, 1000
; --- Einde macro: fmul_round ---
    MULI I, 2
    ADD I, K
    LD L, A
    LD M, I
    LDI B, 32
; --- IF STATEMENT START (ID: 6) ---
    TSTE Z, B
    JMPF __IF_END_6
    JMP CALC_FINISHED
__IF_END_6:
; --- IF STATEMENT END ---
    JMP MANDEL_CORE_LOOP

CALC_FINISHED:
    LDI B, 100
    LDI I, 3
    MSG_START B, I
    MSG_WRITE I, Z
    MSG_WRITE I, X
    MSG_WRITE I, Y
    MSG_DONE I
    AUTOCLOSE