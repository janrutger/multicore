MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    SHARED rnd1 1
    SHARED rnd2 1
    SHARED rnd3 1
    SHARED rnd4 1
    SHARED rnd5 1
    SHARED rnd6 1
    SHARED rnd7 1
    SHARED rnd8 1
    SHARED rnd9 1
    SHARED rnd10 1


    CONST random 7


}

PROGRAM {
    main:
        5 -> A 

        RND32 A random
        A -> [rnd1]

        RND32 A random
        A -> [rnd2]

        RND32 A random
        A -> [rnd3]

        RND32 A random
        A -> [rnd4]

        RND32 A random
        A -> [rnd5]

        RND32 A random
        A -> [rnd6]

        RND32 A random
        A -> [rnd7]

        RND32 A random
        A -> [rnd8]

        RND32 A random
        A -> [rnd9]

        RND32 A random
        A -> [rnd10]
    HALT
}
