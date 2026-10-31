; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI C, 0
    LDI I, 0
    LDI K, 0
    LDI B, 16
    LDI A, 2
    OUT A, 0
    LDI I, 0
; --- REPEAT LOOP START ---
__REP_START_0:
    LDI Z, 1
    STX Z, 1472
    STX Z, 1536
    LD A, I
    LDI C, 4
    MOD A, C
    LDI K, 25000
    MUL A, K
    LDI C, 320000
    SUBI C, 37500
    ADD A, C
    STX A, 1024
    STX A, 1152
    LD B, A
    LD A, I
    LDI C, 4
    DIV A, C
    LDI K, 25000
    MUL A, K
    LDI C, 240000
    SUBI C, 37500
    ADD A, C
    STX A, 1088
    STX A, 1216
    LD C, A
    LD A, C
    LDI K, 240000
    SUB A, K
    DIVI A, 6
    STX A, 1280
    LD A, B
    LDI K, 320000
    SUB A, K
    DIVI A, 6
    MULI A, -1
    STX A, 1344
    LDI A, 2500
    STX A, 1408
    INC I
    LDI B, 16
    TSTE I, B
    JMPF __REP_START_0
; --- REPEAT LOOP END ---
    LDI A, 3000
    STO A, 1600

SIMULATION_TICK:
    LDI I, 0
    LDI B, 16
; --- REPEAT LOOP START ---
__REP_START_1:
; --- Start hygiënische macro: startTask (ID: 1) ---
__M1__spawntask:
    RCONTEXT I, BODY_SIMULATE_accretion
    SUCCES __M1__spawnd
    JMP __M1__spawntask
__M1__spawnd:
; --- Einde macro: startTask ---
    INC I
    LDI B, 16
    TSTE I, B
    JMPF __REP_START_1
; --- REPEAT LOOP END ---
; --- Start hygiënische macro: waitMatrix (ID: 2) ---
__M2__waitMatrix:
    ALLSYNC __M2__waitMatrix
; --- Einde macro: waitMatrix ---
    LDI I, 0
    LDI B, 16
; --- REPEAT LOOP START ---
__REP_START_2:
    LDX A, 1152
    STX A, 1024
    LDX A, 1216
    STX A, 1088
    LDX A, 1536
    STX A, 1472
    INC I
    LDI B, 16
    TSTE I, B
    JMPF __REP_START_2
; --- REPEAT LOOP END ---
    LDM A, 1600
    LDI B, 1
    MOD A, B
    TSTZ A
    JMPF SKIP_DRAW_SPAWN
    LDI Z, 0
    CONTEXT Z, DRAW_WORKER

SKIP_DRAW_SPAWN:
    LDM A, 1600
    DEC A
    STO A, 1600
    TSTZ A
    JMPF SIMULATION_TICK
; --- Start hygiënische macro: waitMatrix (ID: 3) ---
__M3__waitMatrix:
    ALLSYNC __M3__waitMatrix
; --- Einde macro: waitMatrix ---
    HALT

DRAW_WORKER:
    LDI A, 3
    OUT A, 5
    IOSYNC
    LDI I, 0
    LDI B, 16
; --- REPEAT LOOP START ---
__REP_START_4:
    LDX A, 1472
    LDI C, 0
; --- IF STATEMENT START (ID: 3) ---
    TSTG C, A
    JMPF __IF_END_3
    JMP _skip_draw
__IF_END_3:
; --- IF STATEMENT END ---
    LDI A, 12
    OUT A, 1
    LDX A, 1024
    DIVI A, 1000
    OUT A, 2
    LDX A, 1088
    DIVI A, 1000
    OUT A, 3
    LDI A, 2
    OUT A, 5
    IOSYNC
_skip_draw:
    INC I
    LDI B, 16
    TSTE I, B
    JMPF __REP_START_4
; --- REPEAT LOOP END ---
    AUTOCLOSE

BODY_SIMULATE_accretion:
    LDI M, 0
    LD M, I
    LD I, M
    LDX A, 1472
    LDI C, 0
; --- IF STATEMENT START (ID: 5) ---
    TSTG C, A
    JMPF __IF_END_5
    LD I, M
    LDX B, 1024
    LD I, M
    LDX C, 1088
    LD I, M
    STX B, 1152
    LD I, M
    STX C, 1216
    LDI Z, -1
    LD I, M
    STX Z, 1536
    AUTOCLOSE
__IF_END_5:
; --- IF STATEMENT END ---
    LDI Z, 1
    LD I, M
    STX Z, 1536
    LDI X, 0
    LDI Y, 0
    LD I, M
    LDX B, 1024
    LD I, M
    LDX C, 1088
    LDI L, 0
    LDI Z, 16
; --- REPEAT LOOP START ---
__REP_START_9:
    TSTE L, M
    JMPT _skip_self
    LD I, L
    LDX A, 1472
    LDI Z, 0
; --- IF STATEMENT START (ID: 6) ---
    TSTG Z, A
    JMPF __IF_END_6
    JMP _skip_self
__IF_END_6:
; --- IF STATEMENT END ---
    LD I, L
    LDX A, 1024
    LD I, L
    LDX K, 1088
    SUB A, B
    SUB K, C
; --- Start hygiënische macro: fmul_round (ID: 4) ---
    MUL A, A
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fmul_round (ID: 5) ---
    MUL K, K
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
    LDI Z, 45000
; --- IF STATEMENT START (ID: 8) ---
    TSTG Z, A
    JMPF __IF_END_8
; --- IF STATEMENT START (ID: 7) ---
    TSTG L, M
    JMPF __IF_END_7
    LDI Z, -1
    LD I, L
    STX Z, 1536
    LD I, M
    LDX I, 1408
    LD I, L
    LDX K, 1408
    ADD K, I
    LD Z, K
    LD I, M
    LDX A, 1280
    LD I, M
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 6) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD I, L
    LDX K, 1280
    LD I, L
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 7) ---
    MUL K, I
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
; --- Start hygiënische macro: fdiv_round (ID: 8) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
    LDI I, 850
; --- Start hygiënische macro: fmul_round (ID: 9) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD I, M
    STX A, 1280
    LD I, M
    LDX A, 1344
    LD I, M
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 10) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD I, L
    LDX K, 1344
    LD I, L
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 11) ---
    MUL K, I
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
; --- Start hygiënische macro: fdiv_round (ID: 12) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
    LDI I, 850
; --- Start hygiënische macro: fmul_round (ID: 13) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD I, M
    STX A, 1344
    LD I, L
    LDX I, 1408
    LD I, M
    LDX K, 1408
    ADD K, I
    LD I, M
    STX K, 1408
__IF_END_7:
; --- IF STATEMENT END ---
__IF_END_8:
; --- IF STATEMENT END ---
    ADDI A, 400
    LD Z, A
    LD I, L
    LDX A, 1024
    SUB A, B
    LD I, L
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 14) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fdiv_round (ID: 15) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
    ADD X, A
    LD I, L
    LDX A, 1088
    SUB A, C
    LD I, L
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 16) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fdiv_round (ID: 17) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
    ADD Y, A
_skip_self:
    INC L
    LDI Z, 16
    TSTE L, Z
    JMPF __REP_START_9
; --- REPEAT LOOP END ---
    LD I, M
    LDX A, 1280
    LD I, M
    LDX K, 1344
    LD I, A
    LDI Z, 0
; --- IF STATEMENT START (ID: 10) ---
    TSTG I, Z
    JMPF __IF_ELSE_10
; --- Start hygiënische macro: fdivi (ID: 18) ---
    MULI I, 1
    ADDI I, 15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
    JMP __IF_END_10
__IF_ELSE_10:
; --- Start hygiënische macro: fdivi (ID: 19) ---
    MULI I, 1
    ADDI I, -15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
__IF_END_10:
; --- IF STATEMENT END ---
    SUB A, I
    LD I, K
    LDI Z, 0
; --- IF STATEMENT START (ID: 11) ---
    TSTG I, Z
    JMPF __IF_ELSE_11
; --- Start hygiënische macro: fdivi (ID: 20) ---
    MULI I, 1
    ADDI I, 15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
    JMP __IF_END_11
__IF_ELSE_11:
; --- Start hygiënische macro: fdivi (ID: 21) ---
    MULI I, 1
    ADDI I, -15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
__IF_END_11:
; --- IF STATEMENT END ---
    SUB K, I
    ADD A, X
    ADD K, Y
    LD I, M
    STX A, 1280
    LD I, M
    STX K, 1344
    ADD B, A
    ADD C, K
    LDI Z, 10000
; --- IF STATEMENT START (ID: 12) ---
    TSTG Z, B
    JMPF __IF_END_12
    LDI B, 10000
    LDI A, 0
    LD I, M
    STX A, 1280
__IF_END_12:
; --- IF STATEMENT END ---
    LDI Z, 630000
; --- IF STATEMENT START (ID: 13) ---
    TSTG B, Z
    JMPF __IF_END_13
    LDI B, 630000
    LDI A, 0
    LD I, M
    STX A, 1280
__IF_END_13:
; --- IF STATEMENT END ---
    LDI Z, 10000
; --- IF STATEMENT START (ID: 14) ---
    TSTG Z, C
    JMPF __IF_END_14
    LDI C, 10000
    LDI K, 0
    LD I, M
    STX K, 1344
__IF_END_14:
; --- IF STATEMENT END ---
    LDI Z, 470000
; --- IF STATEMENT START (ID: 15) ---
    TSTG C, Z
    JMPF __IF_END_15
    LDI C, 470000
    LDI K, 0
    LD I, M
    STX K, 1344
__IF_END_15:
; --- IF STATEMENT END ---
    LD I, M
    STX B, 1152
    LD I, M
    STX C, 1216
    AUTOCLOSE