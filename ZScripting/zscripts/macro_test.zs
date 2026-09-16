MAP {
    MEMSIZE 1024
    SP 10
    START main

    MACRO WAITING(REG, CONSTANT){
        LDI REG CONSTANT
    LUS:
        DEC REG
        TSTZ REG 
        JMPT LUS
    }

    MACRO LEEG(){
        10 -> A
        5 -> B
        ADD A B
    }
}
PROGRAM {
    main:

    WAITING(A, 10)
    WAITING(B, 20)  

    LEEG()

    HALT
}