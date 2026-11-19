; ==============================================================================
;   STERN-Z32 PLATFORM: CONCURRENT MULTI-WORKER DICE SIMULATION (HEAP EDITION)
;   Doel: Meerdere workers krijgen een input-object (seed), gooien dobbelstenen
;         en updaten een gedeeld tellers-object (6 words) op de heap.
; ==============================================================================

MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; --- Test- & heap-adressen ---
    SHARED HEAP_BASE 128        ; Heap in Shared RAM
    SHARED test_status 1        ; 1 = klaar en geslaagd
    SHARED counts_ptr 1         ; Bewaart de heap-pointer naar het 6-words tellers-object

    CONST modulo_val 6          ; Aantal zijden van de dobbelsteen
    CONST max_rolls 500         ; Aantal worpen per worker

    PRIVATE SEED 1

    ; --- Scratch voor heap- & object-macro's ---
    PRIVATE _hp_req_size 1
    PRIVATE _hp_scan_ptr 1
    PRIVATE _hp_ret_ptr 1
    PRIVATE _hp_tmp 1

    ; --- Scratch voor teller-update in workers ---
    PRIVATE _dice_counts_ptr 1
    PRIVATE _dice_val 1

    SHARED lock1 1
    SHARED lock2 1
    SHARED lock3 1
    SHARED lock4 1
    SHARED lock5 1
    SHARED lock6 1

    INCLUDE rand, heap_init, malloc, heap_read, heap_write, free
}

PROGRAM {
main:
    0 -> I
    0 -> A
    A -> [test_status]
    A -> [counts_ptr]

    ; 1. Initialiseer heap
    heap_init(HEAP_BASE, 128)

    ; 2. Alloceer gedeeld tellers-object (6 words: index 0..5 = oog 1..6) en zet op 0
    6 -> B
    malloc(B)
    B -> [counts_ptr]

    0 -> X
    heap_write(B, 0, X)
    heap_write(B, 1, X)
    heap_write(B, 2, X)
    heap_write(B, 3, X)
    heap_write(B, 4, X)
    heap_write(B, 5, X)

    ; 3. Start 4 workers, elk met een eigen input-object (1 word: seed offset)
    1 -> A
    malloc(A)
    111 -> X
    heap_write(A, 0, X)
    RCONTEXT A DICE_WORKER

    1 -> A
    malloc(A)
    999 -> X
    heap_write(A, 0, X)
    RCONTEXT A DICE_WORKER

    1 -> A
    malloc(A)
    255 -> X
    heap_write(A, 0, X)
    RCONTEXT A DICE_WORKER

    1 -> A
    malloc(A)
    467 -> X
    heap_write(A, 0, X)
    RCONTEXT A DICE_WORKER

WAIT_FOR_ALL:
    ALLSYNC WAIT_FOR_ALL

    1 -> A
    A -> [test_status]
    HALT

DICE_WORKER:
    0 -> I
    0 -> Z

    ; Haal seed-offset uit input-object (register A) en geef input-object direct vrij
    heap_read(A, 0, X)
    X -> [SEED]
    free(A)

    ; Haal pointer naar het gedeelde tellers-object op
    [counts_ptr] -> K
    K -> [_dice_counts_ptr]

    ; --- DE SCHONE REPEAT-LUS ---
    REPEAT X TIMES max_rolls {
        ; 1. Genereer willekeurig getal en pas modulo toe
        rand(A, 24)
        modulo_val -> M
        MOD A, M                  ; A = 0, 1, 2, 3, 4 of 5

        ; 2. Update teller voor het geworpen oog in het tellers-object
        MATCH A {
            0 -> {
                [_dice_counts_ptr] -> K
                ATOMIC [lock1] {
                    heap_read(K, 0, Z)
                    INC Z
                    Z -> [_dice_val]
                    [_dice_val] -> Z
                    heap_write(K, 0, Z)
                }
            }
            1 -> {
                [_dice_counts_ptr] -> K
                ATOMIC [lock2] {
                    heap_read(K, 1, Z)
                    INC Z
                    Z -> [_dice_val]
                    [_dice_val] -> Z
                    heap_write(K, 1, Z)
                }
            }
            2 -> {
                [_dice_counts_ptr] -> K
                ATOMIC [lock3] {
                    heap_read(K, 2, Z)
                    INC Z
                    Z -> [_dice_val]
                    [_dice_val] -> Z
                    heap_write(K, 2, Z)
                }
            }
            3 -> {
                [_dice_counts_ptr] -> K
                ATOMIC [lock4] {
                    heap_read(K, 3, Z)
                    INC Z
                    Z -> [_dice_val]
                    [_dice_val] -> Z
                    heap_write(K, 3, Z)
                }
            }
            4 -> {
                [_dice_counts_ptr] -> K
                ATOMIC [lock4] {
                    heap_read(K, 4, Z)
                    INC Z
                    Z -> [_dice_val]
                    [_dice_val] -> Z
                    heap_write(K, 4, Z)
                }
            }
            DEFAULT -> {
                [_dice_counts_ptr] -> K
                ATOMIC [lock5] {
                    heap_read(K, 5, Z)
                    INC Z
                    Z -> [_dice_val]
                    [_dice_val] -> Z
                    heap_write(K, 5, Z)
                }
            }
        }
    }

    AUTOCLOSE
}