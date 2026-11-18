; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    LDI C, 1024
; --- START ATOMIC BLOCK (ID: 1) ---
__ATOMIC_ACQUIRE_1:
    LOCKP C
    SUCCES __ATOMIC_CRIT_1
    JMP __ATOMIC_ACQUIRE_1
__ATOMIC_CRIT_1:
    LDI K, 777
    STO K, 1025
    UNLOCKP C
; --- END ATOMIC BLOCK ---
    HALT