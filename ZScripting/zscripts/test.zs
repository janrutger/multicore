MAP {
    MEMSIZE 2560
    START main

    SHARED result1 1
    SHARED result2 1

    CONST val 43



    
}

PROGRAM {
    main:
        
        42 -> A 
        -1 -> B
        TST A val
        JMPF error

        A -> [result1]
        JMP DONE


        error:
        B -> [result1]

        DONE:
        HALT
}