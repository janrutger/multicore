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

