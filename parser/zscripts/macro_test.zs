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
}
PROGRAM {
    main:

    WAITING(A, 10)
    WAITING(B, 20)  

    HALT
}