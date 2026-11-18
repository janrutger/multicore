; ==============================================================================
;   STERN-Z32 PLATFORM: CONCURRENT MULTI-WORKER DICE SIMULATION (REPEAT EDITION)
;   Doel: Meerdere workers gooien tegelijk dobbelstenen en updaten atomair de tellers
; ==============================================================================

MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; Gedeelde frequentie-tellers voor oog 1 t/m 6
    SHARED count1 1     ; Adres 1024
    SHARED count2 1     ; Adres 1025
    SHARED count3 1     ; Adres 1026
    SHARED count4 1     ; Adres 1027
    SHARED count5 1     ; Adres 1028
    SHARED count6 1     ; Adres 1029

    ; Dedicated mutexen per teller om maximale concurrentie en minimale lock-contention te garanderen
    SHARED lock1 1
    SHARED lock2 1
    SHARED lock3 1
    SHARED lock4 1
    SHARED lock5 1
    SHARED lock6 1

    CONST modulo_val 6      ; Aantal zijden van de dobbelsteen
    CONST max_rolls 500     ; Aantal worpen per worker

    PRIVATE SEED 1
    
    INCLUDE rand

    MACRO count(counter) {
        [counter] -> K
        INC K
        K -> [counter]
    }
}

PROGRAM {
main:
    ; Lanceer Worker 1 (met seed offset 111)
    111 -> A
    RCONTEXT A DICE_WORKER

    ; Lanceer Worker 2 (met seed offset 999)
    999 -> A
    RCONTEXT A DICE_WORKER

    255 -> A
    RCONTEXT A DICE_WORKER

    467 -> A
    RCONTEXT A DICE_WORKER

WAIT_FOR_ALL:
    ALLSYNC WAIT_FOR_ALL     ; Wacht tot alle parallelle workers klaar zijn
    HALT                     ; Klaar! Bekijk de geheugendump van 1024 t/m 1029.

DICE_WORKER:
    0 -> I
    0 -> Z

    ; Initialiseer de private seed van deze specifieke worker (ontvangen in register A)
    A -> [SEED]

    ; --- DE SCHONE REPEAT-LUS ---
    REPEAT X TIMES max_rolls {
        ; 1. Genereer willekeurig getal en pas modulo toe
        rand(A, 24)
        modulo_val -> M
        MOD A, M              ; A = 0, 1, 2, 3, 4 of 5

        ; 2. Dispatch naar de juiste teller via het MATCH statement
        MATCH A {
            0 -> { 
                ATOMIC [lock1] {
                    count(count1)
                }
            }
            1 -> {
                ATOMIC [lock2] {
                    count(count2)
                }
            }
            2 -> {
                ATOMIC [lock3] {
                    count(count3)
                }
            }
            3 -> {
                ATOMIC [lock4] {
                    count(count4)
                }
            }
            4 -> {
                ATOMIC [lock5] {
                    count(count5)
                }
            }
            DEFAULT -> {
                ATOMIC [lock6] {
                    count(count6)
                }
            }
        }
    }

    AUTOCLOSE
}