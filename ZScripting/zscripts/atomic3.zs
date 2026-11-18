MAP {
    SHARED mutex_pool 4     ; 4 mutex-slots in shared memory (geïnitialiseerd op 0)
    SHARED results 4        ; Hier schrijven we de testuitkomsten (1 = OK, 0 = FOUT)
}

PROGRAM {
    ; ==========================================================
    ; TEST 1: LOCKP op dynamisch pointer-adres (mutex_pool + 2)
    ; ==========================================================
    LDI I, mutex_pool
    ADDI I, 2               ; I wijst nu naar mutex_pool[2]

    LOCKP I                 ; Probeer slot 2 te locken via pointer in I
    FAIL _test1_fail        ; Zou moeten slagen!

    LDI A, 1                ; Test 1 geslaagd
    STO A, results
    JMP _test2

_test1_fail:
    LDI A, 0                ; Test 1 gefaald
    STO A, results

    ; ==========================================================
    ; TEST 2: Contention check via een ander register (K)
    ; ==========================================================
_test2:
    LDI K, mutex_pool
    ADDI K, 2               ; K wijst ook naar mutex_pool[2] (die nu gelocked is!)

    LOCKP K                 ; Tweede lock-poging op bezet adres
    SUCCES _test2_fail      ; Mag NIET slagen!

    LDI A, 1                ; Test 2 geslaagd (LOCKP weigerde netjes)
    LDI I, results
    ADDI I, 1
    STX A, 0                ; results[1] = 1
    JMP _test3

_test2_fail:
    LDI A, 0                ; Test 2 gefaald (dubbele lock toegestaan!)
    LDI I, results
    ADDI I, 1
    STX A, 0                ; results[1] = 0

    ; ==========================================================
    ; TEST 3: UNLOCKP en daarna opnieuw LOCKP
    ; ==========================================================
_test3:
    LDI I, mutex_pool
    ADDI I, 2

    UNLOCKP I               ; Geef mutex_pool[2] vrij via pointer in I
    FAIL _test3_fail

    LOCKP K                 ; Nu zou K hem wél moeten kunnen pakken!
    FAIL _test3_fail

    LDI A, 1                ; Test 3 geslaagd
    LDI I, results
    ADDI I, 2
    STX A, 0                ; results[2] = 1
    
    UNLOCKP K               ; Netjes opruimen
    JMP _done

_test3_fail:
    LDI A, 0                ; Test 3 gefaald
    LDI I, results
    ADDI I, 2
    STX A, 0                ; results[2] = 0

_done:
    HALT
}