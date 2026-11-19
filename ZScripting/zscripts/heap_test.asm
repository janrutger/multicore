; --- BOOTSTRAP VECTOR ---
    JMP MAIN
; ------------------------

main:
    STO 0, 1152
    STO 0, 1153
; --- Start hygiënische macro: heap_init (ID: 1) ---
    LDI I, 0
    STO I, 2559
    STO I, 2558
    STO I, 2557
    LDI I, 1024
    LDI A, 0
    STX A, 0
    LDI A, 128
    STX A, 1
    LDI A, 1024
    ADDI A, 3
    STX A, 2
; --- Einde macro: heap_init ---
    LDI A, 2
; --- Start hygiënische macro: malloc (ID: 2) ---
    STO A, 2559
__M2__hp_lock:
    LOCK 1024
    FAIL __M2__hp_lock
    LDI I, 1024
    ADDI I, 3
    STO I, 2558
    LDI I, 1024
    LDX A, 2
    STO A, 2556
__M2__hp_scan_loop:
    LDM I, 2558
    LDM A, 2556
    TSTE I, A
    JMPT __M2__hp_try_bump
    TSTG I, A
    JMPT __M2__hp_try_bump
    LDX A, 1
    TSTZ A
    JMPT __M2__hp_check_size
    JMP __M2__hp_next_slot
__M2__hp_check_size:
    LDM I, 2558
    LDX A, 2
    LDM I, 2559
    TSTG I, A
    JMPT __M2__hp_next_slot
    LDM A, 2558
    STO A, 2557
    LDM I, 2558
    LDI A, 1
    STX A, 1
    JMP __M2__hp_unlock_ok
__M2__hp_next_slot:
    LDM I, 2558
    LDX A, 2
    ADDI A, 3
    ADD A, I
    STO A, 2558
    JMP __M2__hp_scan_loop
__M2__hp_try_bump:
    LDM A, 2556
    STO A, 2557
    LDM I, 2559
    ADDI I, 3
    ADD A, I
    LDI I, 1024
    LDX I, 1
    ADDI I, 1024
    ADDI I, 3
    TSTG A, I
    JMPT __M2__hp_fail
    LDI I, 1024
    STX A, 2
    LDM I, 2557
    LDI A, 0
    STX A, 0
    LDI A, 1
    STX A, 1
    LDM A, 2559
    STX A, 2
__M2__hp_unlock_ok:
    UNLOCK 1024
    LDM A, 2557
    JMP __M2__hp_done
__M2__hp_fail:
    LDI A, 0
    STO A, 2557
    UNLOCK 1024
__M2__hp_done:
; --- Einde macro: malloc ---
; --- IF STATEMENT START (ID: 0) ---
    TSTZ A
    JMPF __IF_END_0
    STO 99, 1153
    HALT
__IF_END_0:
; --- IF STATEMENT END ---
    LDI X, 10
    LDI Y, 32
; --- Start hygiënische macro: heap_write (ID: 3) ---
__M3__hw_lock:
    LOCKP A
    FAIL __M3__hw_lock
    LD I, A
    ADDI I, 3
    ADDI I, 0
    STX X, 0
__M3__hw_unlock:
    UNLOCKP A
    FAIL __M3__hw_unlock
; --- Einde macro: heap_write ---
; --- Start hygiënische macro: heap_write (ID: 4) ---
__M4__hw_lock:
    LOCKP A
    FAIL __M4__hw_lock
    LD I, A
    ADDI I, 3
    ADDI I, 1
    STX Y, 0
__M4__hw_unlock:
    UNLOCKP A
    FAIL __M4__hw_unlock
; --- Einde macro: heap_write ---
    CONTEXT A, input_worker
    SYNC main_wait_1

main_wait_1:
    SYNC main_wait_1
    LDI B, 2
; --- Start hygiënische macro: malloc (ID: 5) ---
    STO B, 2559
__M5__hp_lock:
    LOCK 1024
    FAIL __M5__hp_lock
    LDI I, 1024
    ADDI I, 3
    STO I, 2558
    LDI I, 1024
    LDX B, 2
    STO B, 2556
__M5__hp_scan_loop:
    LDM I, 2558
    LDM B, 2556
    TSTE I, B
    JMPT __M5__hp_try_bump
    TSTG I, B
    JMPT __M5__hp_try_bump
    LDX B, 1
    TSTZ B
    JMPT __M5__hp_check_size
    JMP __M5__hp_next_slot
__M5__hp_check_size:
    LDM I, 2558
    LDX B, 2
    LDM I, 2559
    TSTG I, B
    JMPT __M5__hp_next_slot
    LDM B, 2558
    STO B, 2557
    LDM I, 2558
    LDI B, 1
    STX B, 1
    JMP __M5__hp_unlock_ok
__M5__hp_next_slot:
    LDM I, 2558
    LDX B, 2
    ADDI B, 3
    ADD B, I
    STO B, 2558
    JMP __M5__hp_scan_loop
__M5__hp_try_bump:
    LDM B, 2556
    STO B, 2557
    LDM I, 2559
    ADDI I, 3
    ADD B, I
    LDI I, 1024
    LDX I, 1
    ADDI I, 1024
    ADDI I, 3
    TSTG B, I
    JMPT __M5__hp_fail
    LDI I, 1024
    STX B, 2
    LDM I, 2557
    LDI B, 0
    STX B, 0
    LDI B, 1
    STX B, 1
    LDM B, 2559
    STX B, 2
__M5__hp_unlock_ok:
    UNLOCK 1024
    LDM B, 2557
    JMP __M5__hp_done
__M5__hp_fail:
    LDI B, 0
    STO B, 2557
    UNLOCK 1024
__M5__hp_done:
; --- Einde macro: malloc ---
; --- IF STATEMENT START (ID: 1) ---
    TSTZ B
    JMPF __IF_END_1
    STO 99, 1153
    HALT
__IF_END_1:
; --- IF STATEMENT END ---
    LDI X, 10
    LDI Y, 32
; --- Start hygiënische macro: heap_write (ID: 6) ---
__M6__hw_lock:
    LOCKP B
    FAIL __M6__hw_lock
    LD I, B
    ADDI I, 3
    ADDI I, 0
    STX X, 0
__M6__hw_unlock:
    UNLOCKP B
    FAIL __M6__hw_unlock
; --- Einde macro: heap_write ---
; --- Start hygiënische macro: heap_write (ID: 7) ---
__M7__hw_lock:
    LOCKP B
    FAIL __M7__hw_lock
    LD I, B
    ADDI I, 3
    ADDI I, 1
    STX Y, 0
__M7__hw_unlock:
    UNLOCKP B
    FAIL __M7__hw_unlock
; --- Einde macro: heap_write ---
    CONTEXT B, calc_worker

wait_join:
    JOIN B, wait_join
; --- Start hygiënische macro: heap_read (ID: 8) ---
__M8__hr_lock:
    LOCKP B
    FAIL __M8__hr_lock
    LD I, B
    ADDI I, 3
    ADDI I, 0
    LDX C, 0
__M8__hr_unlock:
    UNLOCKP B
    FAIL __M8__hr_unlock
; --- Einde macro: heap_read ---
    STO C, 1152
; --- Start hygiënische macro: free (ID: 9) ---
__M9__fr_lock:
    LOCKP B
    FAIL __M9__fr_lock
    STO B, 2556
    LDI B, 0
    LDM I, 2556
    STX B, 1
    LDM B, 2556
__M9__fr_unlock:
    UNLOCKP B
    FAIL __M9__fr_unlock
; --- Einde macro: free ---
    STO 1, 1153
    HALT

input_worker:
; --- Start hygiënische macro: heap_read (ID: 10) ---
__M10__hr_lock:
    LOCKP A
    FAIL __M10__hr_lock
    LD I, A
    ADDI I, 3
    ADDI I, 0
    LDX X, 0
__M10__hr_unlock:
    UNLOCKP A
    FAIL __M10__hr_unlock
; --- Einde macro: heap_read ---
; --- Start hygiënische macro: heap_read (ID: 11) ---
__M11__hr_lock:
    LOCKP A
    FAIL __M11__hr_lock
    LD I, A
    ADDI I, 3
    ADDI I, 1
    LDX Y, 0
__M11__hr_unlock:
    UNLOCKP A
    FAIL __M11__hr_unlock
; --- Einde macro: heap_read ---
; --- Start hygiënische macro: free (ID: 12) ---
__M12__fr_lock:
    LOCKP A
    FAIL __M12__fr_lock
    STO A, 2556
    LDI A, 0
    LDM I, 2556
    STX A, 1
    LDM A, 2556
__M12__fr_unlock:
    UNLOCKP A
    FAIL __M12__fr_unlock
; --- Einde macro: free ---
    AUTOCLOSE

calc_worker:
; --- Start hygiënische macro: heap_read (ID: 13) ---
__M13__hr_lock:
    LOCKP B
    FAIL __M13__hr_lock
    LD I, B
    ADDI I, 3
    ADDI I, 0
    LDX X, 0
__M13__hr_unlock:
    UNLOCKP B
    FAIL __M13__hr_unlock
; --- Einde macro: heap_read ---
; --- Start hygiënische macro: heap_read (ID: 14) ---
__M14__hr_lock:
    LOCKP B
    FAIL __M14__hr_lock
    LD I, B
    ADDI I, 3
    ADDI I, 1
    LDX Y, 0
__M14__hr_unlock:
    UNLOCKP B
    FAIL __M14__hr_unlock
; --- Einde macro: heap_read ---
    ADD X, Y
; --- Start hygiënische macro: heap_write (ID: 15) ---
__M15__hw_lock:
    LOCKP B
    FAIL __M15__hw_lock
    LD I, B
    ADDI I, 3
    ADDI I, 0
    STX X, 0
__M15__hw_unlock:
    UNLOCKP B
    FAIL __M15__hw_unlock
; --- Einde macro: heap_write ---
    CLOSE