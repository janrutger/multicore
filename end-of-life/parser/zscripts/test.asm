; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 5
    LDI B, 10
    SUB A, B
    STO A, 1028
    MUL B, A
    STO B, 1029
    ADD B, A
    STO B, 1030
    DIV B, A
    STO B, 1031
    MULI B, -1
    STO B, 1032
    MULI A, -1
    STO A, 1033
    HALT