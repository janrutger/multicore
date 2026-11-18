; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI A, 111
    RCONTEXT A, DICE_WORKER
    LDI A, 999
    RCONTEXT A, DICE_WORKER
    LDI A, 255
    RCONTEXT A, DICE_WORKER
    LDI A, 467
    RCONTEXT A, DICE_WORKER

WAIT_FOR_ALL:
    ALLSYNC WAIT_FOR_ALL
    HALT

DICE_WORKER:
    LDI I, 0
    LDI Z, 0
    STO A, 2559
    LDI X, 500
; --- REPEAT LOOP START ---
__REP_START_7:
; --- Start hygiënische macro: rand (ID: 1) ---
    LDM A, 2559
    RND32 A, 21
    STO A, 2559
    SHIFTR A, 24
; --- Einde macro: rand ---
    LDI M, 6
    MOD A, M
; --- MATCH STATEMENT START (ID: 6) ---
    TST A, 0
    JMPF __MATCH_6_ARM_1
; --- START ATOMIC BLOCK (ID: 1) ---
__ATOMIC_ACQUIRE_1:
    LOCK 1030
    SUCCES __ATOMIC_CRIT_1
    JMP __ATOMIC_ACQUIRE_1
__ATOMIC_CRIT_1:
; --- Start hygiënische macro: count (ID: 2) ---
    LDM K, 1024
    INC K
    STO K, 1024
; --- Einde macro: count ---
    UNLOCK 1030
; --- END ATOMIC BLOCK ---
    JMP __MATCH_END_6
__MATCH_6_ARM_1:
    TST A, 1
    JMPF __MATCH_6_ARM_2
; --- START ATOMIC BLOCK (ID: 2) ---
__ATOMIC_ACQUIRE_2:
    LOCK 1031
    SUCCES __ATOMIC_CRIT_2
    JMP __ATOMIC_ACQUIRE_2
__ATOMIC_CRIT_2:
; --- Start hygiënische macro: count (ID: 3) ---
    LDM K, 1025
    INC K
    STO K, 1025
; --- Einde macro: count ---
    UNLOCK 1031
; --- END ATOMIC BLOCK ---
    JMP __MATCH_END_6
__MATCH_6_ARM_2:
    TST A, 2
    JMPF __MATCH_6_ARM_3
; --- START ATOMIC BLOCK (ID: 3) ---
__ATOMIC_ACQUIRE_3:
    LOCK 1032
    SUCCES __ATOMIC_CRIT_3
    JMP __ATOMIC_ACQUIRE_3
__ATOMIC_CRIT_3:
; --- Start hygiënische macro: count (ID: 4) ---
    LDM K, 1026
    INC K
    STO K, 1026
; --- Einde macro: count ---
    UNLOCK 1032
; --- END ATOMIC BLOCK ---
    JMP __MATCH_END_6
__MATCH_6_ARM_3:
    TST A, 3
    JMPF __MATCH_6_ARM_4
; --- START ATOMIC BLOCK (ID: 4) ---
__ATOMIC_ACQUIRE_4:
    LOCK 1033
    SUCCES __ATOMIC_CRIT_4
    JMP __ATOMIC_ACQUIRE_4
__ATOMIC_CRIT_4:
; --- Start hygiënische macro: count (ID: 5) ---
    LDM K, 1027
    INC K
    STO K, 1027
; --- Einde macro: count ---
    UNLOCK 1033
; --- END ATOMIC BLOCK ---
    JMP __MATCH_END_6
__MATCH_6_ARM_4:
    TST A, 4
    JMPF __MATCH_6_ARM_5
; --- START ATOMIC BLOCK (ID: 5) ---
__ATOMIC_ACQUIRE_5:
    LOCK 1034
    SUCCES __ATOMIC_CRIT_5
    JMP __ATOMIC_ACQUIRE_5
__ATOMIC_CRIT_5:
; --- Start hygiënische macro: count (ID: 6) ---
    LDM K, 1028
    INC K
    STO K, 1028
; --- Einde macro: count ---
    UNLOCK 1034
; --- END ATOMIC BLOCK ---
    JMP __MATCH_END_6
__MATCH_6_ARM_5:
; --- START ATOMIC BLOCK (ID: 6) ---
__ATOMIC_ACQUIRE_6:
    LOCK 1035
    SUCCES __ATOMIC_CRIT_6
    JMP __ATOMIC_ACQUIRE_6
__ATOMIC_CRIT_6:
; --- Start hygiënische macro: count (ID: 7) ---
    LDM K, 1029
    INC K
    STO K, 1029
; --- Einde macro: count ---
    UNLOCK 1035
; --- END ATOMIC BLOCK ---
__MATCH_END_6:
; --- MATCH STATEMENT END ---
    DEC X
    TSTZ X
    JMPF __REP_START_7
; --- REPEAT LOOP END ---
    AUTOCLOSE