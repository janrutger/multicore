; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI I, 0
    LDI B, 32
    LDI A, 2
    OUT A, 0
    LDI I, 0
; --- REPEAT LOOP START ---
__REP_START_2:
; --- IF STATEMENT START (ID: 0) ---
    TSTZ I
    JMPF __IF_END_0
    LDI A, 320000
    STX A, 1024
    STX A, 1088
    LDI A, 240000
    STX A, 1056
    STX A, 1120
    LDI A, 0
    STX A, 1152
    STX A, 1184
    LDI A, 100000
    STX A, 1216
__IF_END_0:
; --- IF STATEMENT END ---
; --- IF STATEMENT START (ID: 1) ---
    TSTZ I
    JMPT __IF_END_1
    LD A, I
    LDI C, 5
    MOD A, C
    LDI C, 50000
    MUL A, C
    LDI C, 100000
    SUB A, C
    LDI C, 320000
    ADD A, C
    STX A, 1024
    STX A, 1088
    LD A, I
    LDI C, 7
    MOD A, C
    LDI C, 40000
    MUL A, C
    LDI C, 120000
    SUB A, C
    LDI C, 240000
    ADD A, C
    STX A, 1056
    STX A, 1120
    LDX A, 1056
    LDI C, 240000
    SUB A, C
    DIVI A, 10
    STX A, 1152
    LDX A, 1024
    LDI C, 320000
    SUB A, C
    MULI A, -1
    DIVI A, 10
    STX A, 1184
    LDI A, 1000
    STX A, 1216
__IF_END_1:
; --- IF STATEMENT END ---
    INC I
    LDI B, 32
    TSTE I, B
    JMPF __REP_START_2
; --- REPEAT LOOP END ---
    LDI A, 1000
    STO A, 1248

SIMULATION_TICK:
    LDI I, 0
    LDI B, 32
; --- REPEAT LOOP START ---
__REP_START_3:
; --- Start hygiënische macro: startTask (ID: 1) ---
__M1__spawntask:
    RCONTEXT I, BODY_SIMULATE_mass
    SUCCES __M1__spawnd
    JMP __M1__spawntask
__M1__spawnd:
; --- Einde macro: startTask ---
    INC I
    LDI B, 32
    TSTE I, B
    JMPF __REP_START_3
; --- REPEAT LOOP END ---
; --- Start hygiënische macro: waitMatrix (ID: 2) ---
__M2__waitMatrix:
    ALLSYNC __M2__waitMatrix
; --- Einde macro: waitMatrix ---
    LDI I, 0
    LDI B, 32
; --- REPEAT LOOP START ---
__REP_START_4:
    LDX A, 1088
    STX A, 1024
    LDX A, 1120
    STX A, 1056
    INC I
    LDI B, 32
    TSTE I, B
    JMPF __REP_START_4
; --- REPEAT LOOP END ---
    LDM A, 1248
    LDI B, 1
    MOD A, B
    TSTZ A
    JMPF SKIP_DRAW_SPAWN
    LDI Z, 0
    CONTEXT Z, DRAW_WORKER

SKIP_DRAW_SPAWN:
    LDM A, 1248
    DEC A
    STO A, 1248
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
    LDI B, 32
; --- REPEAT LOOP START ---
__REP_START_6:
    LDI A, 12
; --- IF STATEMENT START (ID: 5) ---
    TSTZ I
    JMPF __IF_END_5
    LDI A, 5
__IF_END_5:
; --- IF STATEMENT END ---
    OUT A, 1
    LDX A, 1024
    DIVI A, 1000
    OUT A, 2
    LDX A, 1056
    DIVI A, 1000
    OUT A, 3
    LDI A, 2
    OUT A, 5
    IOSYNC
    INC I
    TSTE I, B
    JMPF __REP_START_6
; --- REPEAT LOOP END ---
    AUTOCLOSE

BODY_SIMULATE_mass:
    LDI M, 0
    LD M, I
    LDI X, 0
    LDI Y, 0
    LD I, M
    LDX B, 1024
    LD I, M
    LDX C, 1056
    LDI L, 0
    LDI Z, 32
; --- REPEAT LOOP START ---
__REP_START_7:
    TSTE L, M
    JMPT _skip_self
    LD I, L
    LDX A, 1024
    LD I, L
    LDX K, 1056
    SUB A, B
    SUB K, C
    DIVI A, 100
    DIVI K, 100
    MUL A, A
    MUL K, K
    ADD A, K
    ADDI A, 200
    LD K, A
    LD I, L
    LDX A, 1024
    SUB A, B
    LD I, L
    LDX I, 1216
    MUL A, I
    DIV A, K
    DIVI A, 10
    ADD X, A
    LD I, L
    LDX A, 1056
    SUB A, C
    LD I, L
    LDX I, 1216
    MUL A, I
    DIV A, K
    DIVI A, 10
    ADD Y, A
_skip_self:
    INC L
    LDI Z, 32
    TSTE L, Z
    JMPF __REP_START_7
; --- REPEAT LOOP END ---
; --- IF STATEMENT START (ID: 8) ---
    TSTZ M
    JMPF __IF_END_8
    LDI B, 320000
    LDI C, 240000
    LD I, M
    STX B, 1088
    LD I, M
    STX C, 1120
    AUTOCLOSE
__IF_END_8:
; --- IF STATEMENT END ---
    LD I, M
    LDX A, 1152
    LD I, M
    LDX K, 1184
    LD I, A
    SHIFTR I, 10
    SUB A, I
    LD I, K
    SHIFTR I, 10
    SUB K, I
    ADD A, X
    ADD K, Y
    LD I, M
    STX A, 1152
    LD I, M
    STX K, 1184
    ADD B, A
    ADD C, K
    LDI I, 10000
; --- IF STATEMENT START (ID: 9) ---
    TSTG I, B
    JMPF __IF_END_9
    LDI B, 10000
    LDI A, 0
    LD I, M
    STX A, 1152
__IF_END_9:
; --- IF STATEMENT END ---
    LDI I, 630000
; --- IF STATEMENT START (ID: 10) ---
    TSTG B, I
    JMPF __IF_END_10
    LDI B, 630000
    LDI A, 0
    LD I, M
    STX A, 1152
__IF_END_10:
; --- IF STATEMENT END ---
    LDI I, 10000
; --- IF STATEMENT START (ID: 11) ---
    TSTG I, C
    JMPF __IF_END_11
    LDI C, 10000
    LDI K, 0
    LD I, M
    STX K, 1184
__IF_END_11:
; --- IF STATEMENT END ---
    LDI I, 470000
; --- IF STATEMENT START (ID: 12) ---
    TSTG C, I
    JMPF __IF_END_12
    LDI C, 470000
    LDI K, 0
    LD I, M
    STX K, 1184
__IF_END_12:
; --- IF STATEMENT END ---
    LD I, M
    STX B, 1088
    LD I, M
    STX C, 1120
    AUTOCLOSE