; ==============================================================================
;  STERN-Z32 PLATFORM: ATOMIC POINTER-INDIRECT (LOCKP) TEST
; ==============================================================================

MAP {
     MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    SHARED my_lock_addr 1   ; Het geheugenadres dat we als mutex gaan gebruiken
    SHARED result_val 1     ; Opslag om te controleren of het kritieke blok draaide
}

PROGRAM {
main:
    ; 1. Laad het numerieke RAM-adres van 'my_lock_addr' in index-register I.
    ;    Hierdoor fungeert I nu als een echte heap-pointer!
    LDI C, my_lock_addr

    ; 2. Atomaire blok via register I.
    ;    Omdat 'I' een register is, herkent de parser dit en genereert hij:
    ;    LOCKP I  ...  UNLOCKP I
    ATOMIC C {
        LDI K, 777
        STO K, result_val
    }

    HALT
}