; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 3
    RBOOT A, CPU_WORKER

leeslus:
    LDI B, 102
    MSG_PROBE B
    FAIL _SKIP_READ_1
    MSG_OPEN I
    MSG_READ I, K
    MSG_CLOSE I
        STO K, 1033
        JMP einde
_SKIP_READ_1:
    JMP leeslus

einde:
    HALT

CPU_WORKER:
    LDI A, 42
    LDI B, 0
    LDI C, 0
    RCONTEXT A, R_CONTEXT
    CPUID A
    STO A, 1026
    PID A
    STO A, 1027
    LDI A, 42
    STO A, 1024

RECEIVE_LOOP:
    LDI B, 101
    MSG_PROBE B
    FAIL _SKIP_READ_2
    MSG_OPEN I
    MSG_READ I, A
    MSG_READ I, C
    MSG_CLOSE I
        STO A, 1031
        STO C, 1032
        JMP END_WORKER
_SKIP_READ_2:
    LDI B, 102
    MSG_PROBE B
    FAIL _SKIP_READ_3
    MSG_OPEN I
    MSG_READ I, A
    MSG_CLOSE I
        LDI I, 1
    MSG_START B, I
    MSG_WRITE I, A
    MSG_DONE I
        JMP END_WORKER
_SKIP_READ_3:
    JMP RECEIVE_LOOP

END_WORKER:
    SUSPEND

R_CONTEXT:
    MUL A, A
    STO A, 1025
    CPUID B
    STO B, 1028
    PID B
    STO B, 1029
    LDI C, 1967
    LDI B, 101
    LDI I, 2
    MSG_START B, I
    MSG_WRITE I, A
    MSG_WRITE I, C
    MSG_DONE I
    LDI B, 102
    LDI I, 1
    MSG_START B, I
    MSG_WRITE I, C
    MSG_DONE I
    AUTOCLOSE