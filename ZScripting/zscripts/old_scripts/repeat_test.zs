MAP {
    START main
    MEMSIZE 1024
    SP 16

    RES res1 1
    RES res2 1
    RES resultaat 1

    IO  sensor_poort 2
}

PROGRAM {
; ==========================================================
;  TEST PROGRAMMA VOOR DE NIEUWE REPEAT FUNCTIONALITEIT
; ==========================================================

main:
    LDI A, 0             ; Reset onze hoofd-accumulator A naar 0

    ; --------------------------------======================
    ;  TEST 1: Pure TIMES loop (Herhaal exact 5 keer)
    ; --------------------------------======================
    REPEAT I TIMES 5 {
        INC A            ; Verhoog A bij elke iteratie
    }
    STO A res1
    ; Na deze lus moet A de waarde 5 hebben.


    ; --------------------------------======================
    ;  TEST 2: Pure UNTIL loop (Herhaal totdat A == 10)
    ; --------------------------------======================
    LDI K 10
    REPEAT UNTIL (A == K) {
        INC A            ; Blijf A verhogen
    }
    TSTG A K
    STO A res2
    ; Na deze lus moet A exact de waarde 10 hebben.


    ; --------------------------------======================
    ;  TEST 3: Gecombineerde loop (Doe 10 keer, TENZIJ sensor == 1)
    ; --------------------------------======================
    LDI B, 0             ; Reset sensor-register B naar 0

    LDI K 1
    REPEAT K TIMES 10 UNTIL (B == K) {
        IN B, sensor_poort  ; Lees de hardwarepoort uit
        INC A               ; Verhoog A (telt hoe vaak we effectief geloopt hebben)
    }

    ; Sla het uiteindelijke resultaat op in het geheugen
    STO A, resultaat
    HALT
}