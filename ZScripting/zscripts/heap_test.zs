; ==========================================================
; TESTSCRIPT: RUNTIME DATA OBJECTS & HEAP MACRO'S (STERN-Z32)
; ==========================================================

MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }

    START main

    ; --- Heap & Scratch geheugen ---
    SHARED result_check 1       ; Hier komt het eindresultaat (10 + 32 = 42)
    SHARED test_status 1        ; 1 = alles geslaagd, 99 = allocatie fout
    SHARED HEAP_BASE 128        ; Heap van 128 words in Shared RAM
    

    PRIVATE _hp_req_size 1
    PRIVATE _hp_scan_ptr 1
    PRIVATE _hp_ret_ptr 1
    PRIVATE _hp_tmp 1

    INCLUDE heap_init, malloc, heap_read, heap_write, free

}

PROGRAM {
main:
    0 -> I 

    0 -> A
    A -> [result_check]
    A -> [test_status]

    ; Initialiseer heap van 128 words
    heap_init(HEAP_BASE, 128)

    ; ======================================================
    ; STAP 1: Input-only object (context zet zelf FREE)
    ; ======================================================
    2 -> A
    malloc(A)                   ; A bevat nu pointer naar Object 1 (size 2)
    IF (A ZERO) TRUE {
        99 -> X
        X -> [test_status]
        HALT
    }

    10 -> X
    32 -> Y
    heap_write(A, 0, X)         ; Object1[0] = 10
    heap_write(A, 1, Y)         ; Object1[1] = 32

    ; Start worker die input leest en object zelf op FREE zet
    CONTEXT A, input_worker
    SYNC main_wait_1
main_wait_1:
    SYNC main_wait_1

    ; ======================================================
    ; STAP 2: Werk-/resultaat-object (hergebruikt Object 1!)
    ; ======================================================
    2 -> B
    malloc(B)                   ; B krijgt exact dezelfde pointer als A terug!
    IF (B ZERO) TRUE {
        99 -> X
        X -> [test_status]
        HALT
    }

    10 -> X
    32 -> Y
    heap_write(B, 0, X)         ; Object2[0] = 10
    heap_write(B, 1, Y)         ; Object2[1] = 32

    CONTEXT B, calc_worker

    ; Oogst voltooide context via JOIN B
wait_join:
    JOIN B, wait_join

    ; Lees resultaat uit payload[0] en ruim object op
    heap_read(B, 0, C)          ; C = 42
    C -> [result_check]
    free(B)

    1 -> A 
    A -> [test_status]
    HALT

; --- Worker 1: Leest input-object en geeft het zelf vrij ---
input_worker:
    0 -> I
    heap_read(A, 0, X)          ; Lees 10
    heap_read(A, 1, Y)          ; Lees 32
    free(A)                     ; Input-only: direct op FREE!
    AUTOCLOSE

; --- Worker 2: Verwerkt data en stuurt pointer terug via CLOSE ---
calc_worker:
    0 -> I
    heap_read(B, 0, X)          ; Lees 10
    heap_read(B, 1, Y)          ; Lees 32
    ADD X, Y                    ; X = 42
    heap_write(B, 0, X)         ; Schrijf resultaat terug in object
    CLOSE                       ; Behoud B voor JOIN in main
}