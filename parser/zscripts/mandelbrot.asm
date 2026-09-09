; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 0
    LDI I, 0
    LDI B, 0
    LDI X, 0
    LDI A, 2
    OUT A, 0
    LDI A, 0
    STO A, 2046
    STO A, 1645
    LDI B, 400
; --- REPEAT LOOP START ---
__REP_START_1:
; --- Start hygiënische macro: startTask (ID: 1) ---
__M1__spawntask:
    RCONTEXT X, MANDEL_WORKER
    SUCCES __M1__spawnd
    CONTEXT X, MANDEL_WORKER
    SUCCES __M1__spawnd
__M1__count:
    LDM A, 2046
    INC A
    STO A, 2046
    LDM I, 1645
    LD A, I
    LD I, A
    LDX A, 1646
; --- IF STATEMENT START (ID: 0) ---
    TSTZ A
    JMPT __M1___IF_END_0
    MULI A, 7
    OUT A, 1
    LD A, I
    LDI B, 20
    MOD A, B
    MULI A, 5
    OUT A, 2
    LD A, I
    DIVI A, 20
    MULI A, 5
    OUT A, 3
    LDI A, 2
    OUT A, 5
    IOSYNC
__M1___IF_END_0:
; --- IF STATEMENT END ---
    INC I
    LDI B, 400
    MOD I, B
    STO I, 1645
    LDI B, 400
    JMP __M1__spawntask
__M1__spawnd:
; --- Einde macro: startTask ---
    INC X
    TSTE X, B
    JMPF __REP_START_1
; --- REPEAT LOOP END ---
; --- Start hygiënische macro: waitMatrix (ID: 2) ---
__M2__waitMatrix:
    ALLSYNC __M2__waitMatrix
; --- Einde macro: waitMatrix ---
    LDM I, 1645
    LDI B, 400
; --- REPEAT LOOP START ---
__REP_START_3:
    LD A, I
    LD I, A
    LDX A, 1646
; --- IF STATEMENT START (ID: 2) ---
    TSTZ A
    JMPT __IF_END_2
    MULI A, 7
    OUT A, 1
    LD A, I
    LDI B, 20
    MOD A, B
    MULI A, 5
    OUT A, 2
    LD A, I
    DIVI A, 20
    MULI A, 5
    OUT A, 3
    LDI A, 2
    OUT A, 5
    IOSYNC
__IF_END_2:
; --- IF STATEMENT END ---
    LDI B, 400
    INC I
    TSTE I, B
    JMPF __REP_START_3
; --- REPEAT LOOP END ---
; --- Start hygiënische macro: waitMatrix (ID: 3) ---
__M3__waitMatrix:
    ALLSYNC __M3__waitMatrix
; --- Einde macro: waitMatrix ---
    HALT

MANDEL_WORKER:
    LDI A, 0
    LDI B, 0
    LDI C, 0
    LDI K, 0
    LDI L, 0
    LDI M, 0
    LDI Y, 0
    LDI Z, 0
    LD A, X
    LDI B, 20
    MOD A, B
    MULI A, 150
    SUBI A, 2000
    LD C, A
    LD A, X
    DIVI A, 20
    MULI A, 150
    SUBI A, 1350
    LD K, A
    LDI L, 0
    LDI M, 0
    LDI Y, 0

MANDEL_LOOP:
    LD A, L
; --- Start hygiënische macro: fmul_round (ID: 4) ---
    MUL A, L
    ADDI A, 500
    DIVI A, 1000
; --- Einde macro: fmul_round ---
    LD B, M
; --- Start hygiënische macro: fmul_round (ID: 5) ---
    MUL B, M
    ADDI B, 500
    DIVI B, 1000
; --- Einde macro: fmul_round ---
    LD Z, A
    ADD Z, B
    LDI I, 4000
; --- IF STATEMENT START (ID: 4) ---
    TSTG Z, I
    JMPF __IF_END_4
    JMP MANDEL_DONE
__IF_END_4:
; --- IF STATEMENT END ---
    LD Z, L
; --- Start hygiënische macro: fmul_round (ID: 6) ---
    MUL Z, M
    ADDI Z, 500
    DIVI Z, 1000
; --- Einde macro: fmul_round ---
    MULI Z, 2
    ADD Z, K
    SUB A, B
    ADD A, C
    LD L, A
    LD M, Z
    INC Y
    LDI I, 32
; --- IF STATEMENT START (ID: 5) ---
    TSTE Y, I
    JMPF __IF_END_5
    JMP MANDEL_DONE
__IF_END_5:
; --- IF STATEMENT END ---
    JMP MANDEL_LOOP

MANDEL_DONE:
    LD I, X
    STX Y, 1646
    AUTOCLOSE