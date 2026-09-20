MAP {
    MEMSIZE 1024
    START main

    RES result 1

    CONST itter 50

}

PROGRAM {
    main:
        0 -> A
        A -> [result]


    REPEAT A TIMES itter {
        spawn:
            CONTEXT A WORKER
            FAIL spawn
    }

    flush:
        SYNC flush

    HALT


    WORKER:
        [result] -> B
        ADD A B

        A -> [result]

        15 -> C
        MUL C B

        AUTOCLOSE
}