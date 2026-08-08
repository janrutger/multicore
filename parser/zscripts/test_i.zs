MAP {
    MEMSIZE 1024
    START main

    RES res_start 1     ; Verwacht: 10
    RES res_addi  1     ; Verwacht: 25  (10 + 15)
    RES res_subi  1     ; Verwacht: 20  (25 - 5)
    RES res_muli  1     ; Verwacht: 80  (20 * 4)
    RES res_divi  1     ; Verwacht: 40  (80 / 2)
}

PROGRAM {
main:
    ; 1. Beginwaarde laden (10)
    10 -> A
    A -> [res_start]

    ; 2. Test ADDI (10 + 15 = 25)
    ADDI A 15
    A -> [res_addi]

    ; 3. Test SUBI (25 - 5 = 20)
    SUBI A 5
    A -> [res_subi]

    ; 4. Test MULI (20 * 4 = 80)
    MULI A 4
    A -> [res_muli]

    ; 5. Test DIVI (80 / 2 = 40)
    DIVI A 2
    A -> [res_divi]

    HALT
}