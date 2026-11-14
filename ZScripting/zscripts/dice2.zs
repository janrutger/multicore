; ==============================================================================
;   STERN-Z32 PLATFORM: CONCURRENT MULTI-WORKER DICE SIMULATION
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
    
    ; MACRO rand(val, size) {
    ;     LDM val SEED       
    ;     RND32 val 21       
    ;     STO val SEED       
    ;     SHIFTR val size    
    ; }
    INCLUDE rand
}

PROGRAM {
main:
    ; Lanceer Worker 1 (met seed offset 111)
    LDI A 111
    RCONTEXT A DICE_WORKER

    ; Lanceer Worker 2 (met seed offset 999)
    LDI A 999
    RCONTEXT A DICE_WORKER

    LDI A 255
    RCONTEXT A DICE_WORKER

    LDI A 467
    RCONTEXT A DICE_WORKER

WAIT_FOR_ALL:
    ALLSYNC WAIT_FOR_ALL     ; Wacht tot alle parallelle workers klaar zijn
    HALT                  ; Klaar! Bekijk de geheugendump van 1024 t/m 1029.

DICE_WORKER:
    0 -> I
    0 -> Z

    ; Initialiseer de private seed van deze specifieke worker (ontvangen in register A)
    STO A SEED
    LDI X, max_rolls      ; X is onze lus-teller per worker

DICE_LOOP:
    ; 1. Genereer willekeurig getal en pas modulo toe
    rand(A, 24)
    LDI M, modulo_val 
    MOD A, M              ; A = 0, 1, 2, 3, 4 of 5

    ; 2. Dispatch naar de juiste teller via if-structuur en bescherm de update ATOMAIR
    LDI B, 0
    TSTE A, B             ; Oog 1?
    JMPF CHECK_TWO
    ATOMIC lock1 {
        LDM K count1
        INC K
        STO K count1
    }
    JMP NEXT_ROLL

CHECK_TWO:
    LDI B, 1
    TSTE A, B             ; Oog 2?
    JMPF CHECK_THREE
    ATOMIC lock2 {
        LDM K count2
        INC K
        STO K count2
    }
    JMP NEXT_ROLL

CHECK_THREE:
    LDI B, 2
    TSTE A, B             ; Oog 3?
    JMPF CHECK_FOUR
    ATOMIC lock3 {
        LDM K count3
        INC K
        STO K count3
    }
    JMP NEXT_ROLL

CHECK_FOUR:
    LDI B, 3
    TSTE A, B             ; Oog 4?
    JMPF CHECK_FIVE
    ATOMIC lock4 {
        LDM K count4
        INC K
        STO K count4
    }
    JMP NEXT_ROLL

CHECK_FIVE:
    LDI B, 4
    TSTE A, B             ; Oog 5?
    JMPF CHECK_SIX
    ATOMIC lock5 {
        LDM K count5
        INC K
        STO K count5
    }
    JMP NEXT_ROLL

CHECK_SIX:                ; Oog 6
    ATOMIC lock6 {
        LDM K count6
        INC K
        STO K count6
    }

NEXT_ROLL:
    DEC X
    TSTZ X
    JMPF DICE_LOOP        ; Herhaal tot alle worpen gedaan zijn

    AUTOCLOSE
}