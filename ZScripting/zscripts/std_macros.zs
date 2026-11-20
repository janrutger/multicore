; ==========================================================
; STERN-Z32 STANDARD MACRO LIBRARY (std_macros.zs)
; ==========================================================

; === DYNAMISCHE TASK DISPATCHER (CIU & Lokaal) ===
MACRO startTask(task, arg) {
    _spawntask:
        RCONTEXT arg task       ; 1. Probeer remote worker via CIU netwerk
        SUCCES _spawnd
        CONTEXT arg task        ; 2. Probeer lokaal op CPU 0
        SUCCES _spawnd
        JMP _spawntask          ; Wacht tot er elders context-ruimte vrijkomt
    _spawnd:
}


MACRO rand(val, size) {
        LDM val SEED       
        RND32 val 21       
        STO val SEED       
        SHIFTR val size    
}

MACRO waitMatrix() {
        _waitMatrix:
        ALLSYNC _waitMatrix
    }


; Fixed-Point Vermenigvuldigingsmacro met Round-to-Nearest afronding
MACRO fmul_round(Rx, Ry, scale, half) {
    MUL Rx, Ry
    ADDI Rx, half
    DIVI Rx, scale
}

MACRO fdiv_round(Rx, denominator, scale_val, half_val) {
    MULI Rx, scale_val
    ADDI Rx, half_val
    DIV Rx, denominator
}

; ==========================================================
; HEAP & RUNTIME OBJECT MACROS (MAIN-PROCES HEAP)
; Object layout: [0]=Mutex, [1]=Status (0=FREE,1=ALLOC), [2]=Size, [3..]=Payload
; Heap header:   [0]=Mutex, [1]=Size, [2]=Bumper
; ==========================================================

MACRO heap_init(heap_base, heap_size) {
    LDI I, 0
    STO I, _hp_req_size
    STO I, _hp_scan_ptr
    STO I, _hp_ret_ptr

    ; [heap_base + 0] = 0 (mutex vrij)
    LDI I, heap_base
    LDI A, 0
    STX A, 0

    ; [heap_base + 1] = heap_size
    LDI A, heap_size
    STX A, 1

    ; [heap_base + 2] = heap_base + 3 (bumper start)
    LDI A, heap_base
    ADDI A, 3
    STX A, 2
}

MACRO malloc(rx) {
    ; STO rx, _hp_req_size

    _hp_lock:
        LOCK HEAP_BASE
        FAIL _hp_lock

    STO rx, _hp_req_size

    ; scan_ptr = HEAP_BASE + 3
    LDI I, HEAP_BASE
    ADDI I, 3
    STO I, _hp_scan_ptr

    ; _hp_tmp = bumper (op HEAP_BASE + 2)
    LDI I, HEAP_BASE
    LDX rx, 2
    STO rx, _hp_tmp

    _hp_scan_loop:
        LDM I, _hp_scan_ptr
        LDM rx, _hp_tmp
        TSTE I, rx
        JMPT _hp_try_bump
        TSTG I, rx
        JMPT _hp_try_bump

        ; Lees status op [scan_ptr + 1]
        LDX rx, 1
        TSTZ rx
        JMPT _hp_check_size
        JMP _hp_next_slot

    _hp_check_size:
        ; Lees slot-size op [scan_ptr + 2]
        LDM I, _hp_scan_ptr
        LDX rx, 2
        LDM I, _hp_req_size

        ; slot_size >= req_size  <=>  NOT (req_size > slot_size)
        TSTG I, rx
        JMPT _hp_next_slot

        ; Hergebruik slot op _hp_scan_ptr
        LDM rx, _hp_scan_ptr
        STO rx, _hp_ret_ptr

        LDM I, _hp_scan_ptr
        LDI rx, 1
        STX rx, 1
        JMP _hp_unlock_ok

    _hp_next_slot:
        ; scan_ptr = scan_ptr + 3 + slot_size
        LDM I, _hp_scan_ptr
        LDX rx, 2
        ADDI rx, 3
        ADD rx, I
        STO rx, _hp_scan_ptr
        JMP _hp_scan_loop

    _hp_try_bump:
        ; ret_ptr = huidige bumper
        LDM rx, _hp_tmp
        STO rx, _hp_ret_ptr

        ; nieuwe_bumper = bumper + req_size + 3
        LDM I, _hp_req_size
        ADDI I, 3
        ADD rx, I

        ; heap_einde = HEAP_BASE + 3 + heap_size
        LDI I, HEAP_BASE
        LDX I, 1
        ADDI I, HEAP_BASE
        ADDI I, 3

        ; Als nieuwe_bumper > heap_einde -> fail
        TSTG rx, I
        JMPT _hp_fail

        ; Update bumper op [HEAP_BASE + 2]
        LDI I, HEAP_BASE
        STX rx, 2

        ; Initialiseer object header op _hp_ret_ptr
        LDM I, _hp_ret_ptr
        LDI rx, 0
        STX rx, 0
        LDI rx, 1
        STX rx, 1
        LDM rx, _hp_req_size
        STX rx, 2

    _hp_unlock_ok:
        UNLOCK HEAP_BASE
        LDM rx, _hp_ret_ptr
        JMP _hp_done

    _hp_fail:
        LDI rx, 0
        STO rx, _hp_ret_ptr
        UNLOCK HEAP_BASE

    _hp_done:
}

MACRO heap_read(ptr_reg, idx_val, out_reg) {
    _hr_lock:
        LOCKP ptr_reg
        FAIL _hr_lock

    LD I, ptr_reg
    ADDI I, 3
    ADDI I, idx_val
    LDX out_reg, 0

    _hr_unlock:
        UNLOCKP ptr_reg
        FAIL _hr_unlock
}

MACRO heap_write(ptr_reg, idx_val, val_reg) {
    _hw_lock:
        LOCKP ptr_reg
        FAIL _hw_lock

    LD I, ptr_reg
    ADDI I, 3
    ADDI I, idx_val
    STX val_reg, 0

    _hw_unlock:
        UNLOCKP ptr_reg
        FAIL _hw_unlock
}

MACRO free(ptr_reg) {
    _fr_base:
        LOCK HEAP_BASE
        FAIL _fr_base

    _fr_lock:
        LOCKP ptr_reg
        FAIL _fr_lock

    STO ptr_reg, _hp_tmp
    LDI ptr_reg, 0
    LDM I, _hp_tmp
    STX ptr_reg, 1
    LDM ptr_reg, _hp_tmp

    _fr_unlock:
        UNLOCKP ptr_reg
        FAIL _fr_unlock

    UNLOCK HEAP_BASE
}