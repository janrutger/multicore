; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI B, 0
    LDI C, 0
    LDI K, 0
    LDI X, 0
    LDI Y, 0
    LDI Z, 0
    LDI A, 2
    OUT A, 0
    LDI A, 1
    RBOOT A, SIMULATION_DIRECTOR

RENDER_LISTEN_LOOP:
    LDI B, 200
    MSG_PROBE B
    FAIL _SKIP_READ_1
    MSG_OPEN I
    MSG_CLOSE I
        LDI A, 3
        OUT A, 5
        IOSYNC
        LDI A, 3
        OUT A, 1
        LDI A, 320000
        DIVI A, 1000
        OUT A, 2
        LDI A, 240000
        DIVI A, 1000
        OUT A, 3
        LDI A, 2
        OUT A, 5
        IOSYNC
_SKIP_READ_1:
    LDI K, 201
    MSG_PROBE K
    FAIL _SKIP_READ_2
    MSG_OPEN I
    MSG_READ I, A
    MSG_READ I, X
    MSG_READ I, Y
    MSG_READ I, Z
    MSG_CLOSE I
        LDI C, 0
        ; --- IF STATEMENT START (ID: 0) ---
    TSTG C, Z
    JMPF __IF_END_0
    JMP _skip_server_plot
__IF_END_0:
; --- IF STATEMENT END ---
        LDI C, 12
        OUT C, 1
        LD C, X
        DIVI C, 1000
        OUT C, 2
        LD C, Y
        DIVI C, 1000
        OUT C, 3
        LDI C, 2
        OUT C, 5
        IOSYNC
        _skip_server_plot:
_SKIP_READ_2:
    LDI B, 202
    MSG_PROBE B
    FAIL _SKIP_READ_3
    MSG_OPEN I
    MSG_CLOSE I
_SKIP_READ_3:
    LDI B, 999
    MSG_PROBE B
    FAIL _SKIP_READ_4
    MSG_OPEN I
    MSG_CLOSE I
        HALT
_SKIP_READ_4:
    JMP RENDER_LISTEN_LOOP

SIMULATION_DIRECTOR:
    LDI A, 0
    LDI B, 0
    LDI C, 0
    LDI I, 0
    LDI K, 0
    LDI L, 0
    LDI M, 0
    LDI X, 0
    LDI Y, 0
    LDI Z, 0
    LDI B, 12
    LDI A, 0
    STO A, 1600
    LDI A, 12
    LDI Z, 16
; --- IF STATEMENT START (ID: 1) ---
    TSTG A, Z
    JMPF __IF_ELSE_1
    LDI X, 8
    JMP __IF_END_1
__IF_ELSE_1:
    LDI X, 4
__IF_END_1:
; --- IF STATEMENT END ---
    LDI A, 12
    LD Z, X
    DIV A, Z
    LD Y, A
    LD A, X
    SUBI A, 1
    LDI K, 12500
    MUL A, K
    LD L, A
    LD A, Y
    SUBI A, 1
    LDI K, 12500
    MUL A, K
    LD M, A
    LDI I, 0
; --- REPEAT LOOP START ---
__REP_START_2:
    LDI Z, 1
    STX Z, 1472
    STX Z, 1536
    LD A, I
    LD C, X
    MOD A, C
    LDI K, 25000
    MUL A, K
    LDI C, 320000
    SUB C, L
    ADD A, C
    STX A, 1024
    STX A, 1152
    LD B, A
    LD A, I
    LD C, X
    DIV A, C
    LDI K, 25000
    MUL A, K
    LDI C, 240000
    SUB C, M
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
    LDI B, 12
    TSTE I, B
    JMPF __REP_START_2
; --- REPEAT LOOP END ---
    LDI A, 2500
    STO A, 1601

SIMULATION_TICK:
    LDI I, 0
    LDI B, 12
; --- REPEAT LOOP START ---
__REP_START_3:
; --- Start hygiënische macro: startTask (ID: 1) ---
__M1__spawntask:
    RCONTEXT I, BODY_SIMULATE_accretion
    SUCCES __M1__spawnd
    JMP __M1__spawntask
__M1__spawnd:
; --- Einde macro: startTask ---
    INC I
    LDI B, 12
    TSTE I, B
    JMPF __REP_START_3
; --- REPEAT LOOP END ---
; --- Start hygiënische macro: waitMatrix (ID: 2) ---
__M2__waitMatrix:
    ALLSYNC __M2__waitMatrix
; --- Einde macro: waitMatrix ---
    LDI B, 200
    LDI I, 0
    MSG_START B, I
    MSG_DONE I
    LDI M, 0
    LDI B, 12

SWAP_LOOP:
    LD I, M
    LDX A, 1152
    LD I, M
    STX A, 1024
    LD I, M
    LDX A, 1216
    LD I, M
    STX A, 1088
    LD I, M
    LDX A, 1536
    LD I, M
    STX A, 1472
    LDI B, 201
    LD I, M
    LDX X, 1024
    LD I, M
    LDX Y, 1088
    LD I, M
    LDX Z, 1472
    LDI I, 4
    MSG_START B, I
    MSG_WRITE I, M
    MSG_WRITE I, X
    MSG_WRITE I, Y
    MSG_WRITE I, Z
    MSG_DONE I
    INC M
    LDI B, 12
; --- IF STATEMENT START (ID: 4) ---
    TSTE M, B
    JMPT __IF_END_4
    JMP SWAP_LOOP
__IF_END_4:
; --- IF STATEMENT END ---
    LDI B, 202
    LDI I, 0
    MSG_START B, I
    MSG_DONE I
    LDM A, 1601
    DEC A
    STO A, 1601
    TSTZ A
    JMPF SIMULATION_TICK
    LDI B, 999
    LDI I, 0
    MSG_START B, I
    MSG_DONE I
    HALT

BODY_SIMULATE_accretion:
    LDI M, 0
    LD M, I
    LDI A, 0
    LDI B, 0
    LDI C, 0
    LDI K, 0
    LDI L, 0
    LDI Z, 0
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
    LDI Z, 12
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
; --- Start hygiënische macro: fmul_round (ID: 3) ---
    MUL A, A
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fmul_round (ID: 4) ---
    MUL K, K
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
    LDI Z, 35000
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
; --- Start hygiënische macro: fmul_round (ID: 5) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD I, L
    LDX K, 1280
    LD I, L
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 6) ---
    MUL K, I
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
; --- Start hygiënische macro: fdiv_round (ID: 7) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
    LD I, M
    STX A, 1280
    LD I, M
    LDX A, 1344
    LD I, M
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 8) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD I, L
    LDX K, 1344
    LD I, L
    LDX I, 1408
; --- Start hygiënische macro: fmul_round (ID: 9) ---
    MUL K, I
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
; --- Start hygiënische macro: fdiv_round (ID: 10) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
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
; --- Start hygiënische macro: fmul_round (ID: 11) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fdiv_round (ID: 12) ---
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
; --- Start hygiënische macro: fmul_round (ID: 13) ---
    MUL A, I
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fdiv_round (ID: 14) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, Z
; --- Einde macro: fdiv_round ---
    ADD Y, A
_skip_self:
    INC L
    LDI Z, 12
    TSTE L, Z
    JMPF __REP_START_9
; --- REPEAT LOOP END ---
    LDM I, 1600
    LDI Z, 0
; --- IF STATEMENT START (ID: 10) ---
    TSTG I, Z
    JMPF __IF_END_10
    LDI A, 320000
    SUB A, B
    LD L, A
    LDI A, 240000
    SUB A, C
    LD Z, A
    LD A, L
; --- Start hygiënische macro: fmul_round (ID: 15) ---
    MUL A, A
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD K, Z
; --- Start hygiënische macro: fmul_round (ID: 16) ---
    MUL K, K
    ADDI K, 500
    DIVI K, 1000
; --- Einde macro: fmul_round ---
    ADD A, K
    ADDI A, 400
    LD I, A
    LD A, L
    LDM K, 1600
; --- Start hygiënische macro: fmul_round (ID: 17) ---
    MUL A, K
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fdiv_round (ID: 18) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, I
; --- Einde macro: fdiv_round ---
    ADD X, A
    LD A, Z
    LDM K, 1600
; --- Start hygiënische macro: fmul_round (ID: 19) ---
    MUL A, K
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
; --- Start hygiënische macro: fdiv_round (ID: 20) ---
    MULI A, 1000
    ADDI A, 500
    DIV A, I
; --- Einde macro: fdiv_round ---
    ADD Y, A
__IF_END_10:
; --- IF STATEMENT END ---
    LD I, M
    LDX A, 1280
    LD I, M
    LDX K, 1344
    LD I, A
    LDI Z, 0
; --- IF STATEMENT START (ID: 11) ---
    TSTG I, Z
    JMPF __IF_ELSE_11
; --- Start hygiënische macro: fdivi (ID: 21) ---
    MULI I, 1
    ADDI I, 15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
    JMP __IF_END_11
__IF_ELSE_11:
; --- Start hygiënische macro: fdivi (ID: 22) ---
    MULI I, 1
    ADDI I, -15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
__IF_END_11:
; --- IF STATEMENT END ---
    SUB A, I
    LD I, K
    LDI Z, 0
; --- IF STATEMENT START (ID: 12) ---
    TSTG I, Z
    JMPF __IF_ELSE_12
; --- Start hygiënische macro: fdivi (ID: 23) ---
    MULI I, 1
    ADDI I, 15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
    JMP __IF_END_12
__IF_ELSE_12:
; --- Start hygiënische macro: fdivi (ID: 24) ---
    MULI I, 1
    ADDI I, -15000
    DIVI I, 30000
; --- Einde macro: fdivi ---
__IF_END_12:
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
; --- IF STATEMENT START (ID: 13) ---
    TSTG Z, B
    JMPF __IF_END_13
    LDI B, 10000
    LDI A, 0
    LD I, M
    STX A, 1280
    LDM A, 1600
    ADDI A, 3000
    STO A, 1600
__IF_END_13:
; --- IF STATEMENT END ---
    LDI Z, 630000
; --- IF STATEMENT START (ID: 14) ---
    TSTG B, Z
    JMPF __IF_END_14
    LDI B, 630000
    LDI A, 0
    LD I, M
    STX A, 1280
    LDM A, 1600
    ADDI A, 3000
    STO A, 1600
__IF_END_14:
; --- IF STATEMENT END ---
    LDI Z, 10000
; --- IF STATEMENT START (ID: 15) ---
    TSTG Z, C
    JMPF __IF_END_15
    LDI C, 10000
    LDI K, 0
    LD I, M
    STX K, 1344
    LDM A, 1600
    ADDI A, 3000
    STO A, 1600
__IF_END_15:
; --- IF STATEMENT END ---
    LDI Z, 470000
; --- IF STATEMENT START (ID: 16) ---
    TSTG C, Z
    JMPF __IF_END_16
    LDI C, 470000
    LDI K, 0
    LD I, M
    STX K, 1344
    LDM A, 1600
    ADDI A, 3000
    STO A, 1600
__IF_END_16:
; --- IF STATEMENT END ---
    LD I, M
    STX B, 1152
    LD I, M
    STX C, 1216
    AUTOCLOSE