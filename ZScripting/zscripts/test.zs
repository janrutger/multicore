MAP {
    MEMSIZE 2560
    START main
    RES notused 513

    CONST getal -3
}

PROGRAM {
    main:
        5 -> A
        10 -> B

        

        SUB A B
        STO A 1028

        MUL B A
        STO B 1029

        ADD B A
        STO B 1030

        DIV B A
        STO B 1031

        MULI B -1
        STO B 1032

        MULI A getal
        -1 -> B
        DIV A B
        STO A 1033


        HALT
}