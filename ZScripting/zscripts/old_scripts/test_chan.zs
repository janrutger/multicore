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
    SHARED message_tag 1
    SHARED message_payload 1
    SHARED message_payload2 1
    SHARED message_cpu0 1

    CONST tag 101
}

PROGRAM {
main:
    3 -> A                 ; Channel ID 2 (CPU 2)
    RBOOT A CPU_WORKER

leeslus:
    102 -> B
    READ B (K) {
        K -> [message_cpu0]
        JMP einde
    }
    JMP leeslus


einde:
    HALT


CPU_WORKER:
    42 -> A
    0 -> B
    0 -> C
    RCONTEXT A R_CONTEXT

    CPUID A
    A -> [cpu_cpu]

    PID A
    A -> [CPU_parent]

    42 -> A
    A -> [result_from_CPU]

;--- MAILBOX ONTVANGST LUS IN CPU_WORKER ---
RECEIVE_LOOP:

    tag -> B    ; TAG in B
    READ B (A, C) {
        A -> [message_payload]
        C -> [message_payload2]
        ; JMP END_WORKER
    }

    102 -> B
    READ B (A){
        WRITE B (A)         ; stuur door naar CPU0
        ; JMP END_WORKER
    }

    999 -> B
    READ B () {
        JMP END_WORKER
    }

    JMP RECEIVE_LOOP

   
END_WORKER:
    SUSPEND


R_CONTEXT:
    
    MUL A A                ; A = 42 * 42 = 1764
    A -> [result_from_context]

    CPUID B
    B -> [context_cpu]

    PID B
    B -> [parent_cpu_id]

    1967 -> C

    ;--- VERSTUUR BEREKENING VIA MAILBOX NAAR PARENT CPU ---
    tag -> B               ; B = TAG 101 (Event ID: Rekenresultaat)
    WRITE B (A, C)


    102 -> B
    WRITE B (C)

    999 -> B
    WRITE B ()

    AUTOCLOSE
}