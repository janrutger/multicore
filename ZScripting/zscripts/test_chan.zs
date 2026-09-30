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
}

PROGRAM {
main:
    2 -> A                 ; Channel ID 2 (CPU 2)
    RBOOT A CPU_WORKER

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
    MSG_OPEN A             ; Probeer inkomend bericht te openen (A ontvangt read_slotID)
    FAIL RECEIVE_LOOP    ; Geen VALID bericht klaar? Spring naar RECEIVE_LOOP

    ; A bevat nu het actieve read_slotID
    MSG_PROBE A, B         ; B ontvangt de TAG (101) uit de header
    B -> [message_tag]

    MSG_READ A, C          ; C ontvangt het berekende datawoord (1764)
    C -> [message_payload]

    MSG_CLOSE A            ; Geef het FIFO-slot vrij op FREE / EMPTY
    JMP END_WORKER

   


END_WORKER:
    SUSPEND


R_CONTEXT:
    
    MUL A A                ; A = 42 * 42 = 1764
    A -> [result_from_context]

    CPUID B
    B -> [context_cpu]

    PID B
    B -> [parent_cpu_id]

    ;--- VERSTUUR BEREKENING VIA MAILBOX NAAR PARENT CPU ---
    101 -> B               ; B = TAG 101 (Event ID: Rekenresultaat)
    1 -> C                 ; C = Message Size (1 datawoord)

    MSG_START B, C         ; C ontvangt tx_slotID (gaat automatisch naar PID!)
    MSG_WRITE C, A         ; Schrijf de berekende waarde 1764 (A)
    MSG_DONE C             ; Valideer het bericht op de Parent CPU (status -> VALID)

    AUTOCLOSE
}