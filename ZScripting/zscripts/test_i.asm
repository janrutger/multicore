; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 10
    STO A, 1023
    ADDI A, 15
    STO A, 1022
    SUBI A, 5
    STO A, 1021
    MULI A, 4
    STO A, 1020
    DIVI A, 2
    STO A, 1019
    HALT