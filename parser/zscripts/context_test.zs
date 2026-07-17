MAP {
    START   main
    MEMSIZE 1024
    SP 10

    RES adres 1
   

    CONST bron 5
    CONST itter 100

    IO      X_value   2

    MACRO INIT(arg1, arg2) {
        LDI A arg1             ; Bronwaarde voor de threads 
        LDI I 0                ; Lus-teller I = 0
        LDI Y arg2             ; De doelwaarde (15 iteraties)
        LDI X 0                ; Totaalteller X = 0
    }

    MACRO SET_AND_OUT(reg, waarde, poort) {
        LDI reg, waarde
        OUT reg, poort
    }
}

PROGRAM {
main:
; ==========================================================
;  15x CONTEXT STRESSTEST (Gecorrigeerd)
; ==========================================================
INIT(bron, itter)

SPAWN_LOOP:
    TSTE I Y            
    JMPT FLUSH_REMAINING 

    CONTEXT A THREAD_WORKER 
    FAIL MATRIX_FULL_HANDLER  

    INC I   

    JOIN B SPAWN_LOOP
    ADD X B

    JMP SPAWN_LOOP      

MATRIX_FULL_HANDLER:
    ; Oogst in register B in plaats van A! Hierdoor blijft Master-register A intact.
    JOIN B MATRIX_FULL_HANDLER 
    
    ADD X B             ; Tel het resultaat uit B op bij het totaal X

    JMP SPAWN_LOOP

; ==========================================================
;  FINALE FLUSH
; ==========================================================
FLUSH_REMAINING:
    ; Oogst ook hier in register B!
    JOIN B ALL_DONE     

    ADD X B
    JMP FLUSH_REMAINING

ALL_DONE:

    SYNC FLUSH_REMAINING

    STO X adres           ; Sla het eindresultaat op op adres 512

    HALT                

; ==========================================================
;  PARALLELLE WORKER THREAD CODE
; ==========================================================
THREAD_WORKER: 
    LDI M 42
    LDI L 42
    MUL M L

    LDI B 1             
    MUL B A  

    RETURN B
    ;CLOSE
}
