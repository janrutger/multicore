MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    SHARED result_from_CPU 1
    SHARED result_from_context 1
    SHARED cpu_cpu 1
    SHARED CPU_parent 1
    SHARED context_cpu 1
    SHARED parent_cpu_id 1
    
}

PROGRAM {
main:
    2 -> A         ; Channel ID in A
    RBOOT A CPU_WORKER

    HALT


CPU_WORKER:
    42 -> A
    RCONTEXT A R_CONTEXT

syncwait:
    ALLSYNC syncwait

    A -> [result_from_CPU]

    PID A
    A -> [CPU_parent]


    CPUID A
    A -> [cpu_cpu]

    SUSPEND


R_CONTEXT:
    MUL A A 
    A -> [result_from_context]

    CPUID A
    A -> [context_cpu]

    PID A 
    A -> [parent_cpu_id]

    AUTOCLOSE
    
}