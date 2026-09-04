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
    LDI I, 399
; --- REPEAT LOOP START ---
__REP_START_2:
    STX A, 2159
    STX A, 1759
    DEC I
    TSTZ I
    JMPF __REP_START_2
; --- REPEAT LOOP END ---
    LDI A, 70
    LDI I, 350
    STX A, 2159
    LDI A, 150
    STO A, 1757

SIMULATIE_STAP:
    LDI X, 0
    LDI A, 0
    STO A, 1758
    LDI B, 400
; --- REPEAT LOOP START ---
__REP_START_3:
; --- Start hygiënische macro: startTask (ID: 1) ---
__M1__spawntask:
    RCONTEXT X, HEAT_WORKER
    FAIL __M1__count
    JMP __M1__spawnd
__M1__count:
    LDM A, 2559
    INC A
    STO A, 2559
    LDM I, 1758
    LDI B, 400
; --- IF STATEMENT START (ID: 0) ---
    TSTE I, B
    JMPF __M1___IF_END_0
    LDI B, 400
    JMP __M1__spawntask
__M1___IF_END_0:
; --- IF STATEMENT END ---
    LD A, I
    LD I, A
    LDX A, 2159
    INC I
    STO I, 1758
    DEC I
; --- IF STATEMENT START (ID: 1) ---
    TSTZ A
    JMPT __M1___IF_END_1
    DIVI A, 5
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
__M1___IF_END_1:
; --- IF STATEMENT END ---
    LDI B, 400
    JMP __M1__spawntask
__M1__spawnd:
; --- Einde macro: startTask ---
    INC X
    TSTE X, B
    JMPF __REP_START_3
; --- REPEAT LOOP END ---
; --- Start hygiënische macro: waitMatrix (ID: 2) ---
__M2__waitMatrix:
    ALLSYNC __M2__waitMatrix
; --- Einde macro: waitMatrix ---
    LDM I, 1758
    LDI B, 400
; --- REPEAT LOOP START ---
__REP_START_5:
    LD A, I
    LD I, A
    LDX A, 2159
; --- IF STATEMENT START (ID: 4) ---
    TSTZ A
    JMPT __IF_END_4
    DIVI A, 5
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
__IF_END_4:
; --- IF STATEMENT END ---
    LDI B, 400
    INC I
    TSTE I, B
    JMPF __REP_START_5
; --- REPEAT LOOP END ---
    LDI I, 0
    LDI I, 399
; --- REPEAT LOOP START ---
__REP_START_6:
    LDX A, 1759
    STX A, 2159
    DEC I
    TSTZ I
    JMPF __REP_START_6
; --- REPEAT LOOP END ---
    LDM A, 1757
    DEC A
    STO A, 1757
    TSTZ A
    JMPF SIMULATIE_STAP
; --- Start hygiënische macro: waitMatrix (ID: 3) ---
__M3__waitMatrix:
    ALLSYNC __M3__waitMatrix
; --- Einde macro: waitMatrix ---
    HALT

HEAT_WORKER:
    LDI A, 0
    LDI B, 0
    LDI I, 0
    LDI M, 0
    LDI B, 0
; --- IF STATEMENT START (ID: 7) ---
    TSTE X, B
    JMPF __IF_END_7
    LDI A, 0
    LD I, X
    STX A, 1759
    AUTOCLOSE
__IF_END_7:
; --- IF STATEMENT END ---
    LDI B, 19
; --- IF STATEMENT START (ID: 8) ---
    TSTE X, B
    JMPF __IF_END_8
    LDI A, 0
    LD I, X
    STX A, 1759
    AUTOCLOSE
__IF_END_8:
; --- IF STATEMENT END ---
    LDI B, 380
; --- IF STATEMENT START (ID: 9) ---
    TSTE X, B
    JMPF __IF_END_9
    LDI A, 0
    LD I, X
    STX A, 1759
    AUTOCLOSE
__IF_END_9:
; --- IF STATEMENT END ---
    LDI B, 399
; --- IF STATEMENT START (ID: 10) ---
    TSTE X, B
    JMPF __IF_END_10
    LDI A, 0
    LD I, X
    STX A, 1759
    AUTOCLOSE
__IF_END_10:
; --- IF STATEMENT END ---
    LDI B, 350
; --- IF STATEMENT START (ID: 11) ---
    TSTE X, B
    JMPF __IF_END_11
    LDI A, 70
    LD I, X
    STX A, 1759
    AUTOCLOSE
__IF_END_11:
; --- IF STATEMENT END ---
    LD A, X
    SUBI A, 20
    LDI B, 20
; --- IF STATEMENT START (ID: 12) ---
    TSTG B, X
    JMPF __IF_END_12
    ADDI A, 400
__IF_END_12:
; --- IF STATEMENT END ---
    LD I, A
    LDX A, 2159
    LD B, X
    ADDI B, 20
    LDI M, 380
    DEC M
; --- IF STATEMENT START (ID: 13) ---
    TSTG X, M
    JMPF __IF_END_13
    SUBI B, 400
__IF_END_13:
; --- IF STATEMENT END ---
    LD I, B
    LDX B, 2159
    ADD A, B
    LD M, X
    LDI B, 20
    MOD M, B
    LD B, X
    DEC B
; --- IF STATEMENT START (ID: 14) ---
    TSTZ M
    JMPF __IF_END_14
    ADDI B, 20
__IF_END_14:
; --- IF STATEMENT END ---
    LD I, B
    LDX B, 2159
    ADD A, B
    LD M, X
    LDI B, 20
    MOD M, B
    SUBI M, 19
    LD B, X
    INC B
; --- IF STATEMENT START (ID: 15) ---
    TSTZ M
    JMPF __IF_END_15
    SUBI B, 20
__IF_END_15:
; --- IF STATEMENT END ---
    LD I, B
    LDX B, 2159
    ADD A, B
    ADDI A, 3
    DIVI A, 4
    LD I, X
    STX A, 1759
    AUTOCLOSE