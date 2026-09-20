MAP {
    MEMSIZE 1024
    START main

    RES result 11

    CONST FP-scale 100
    CONST FP-half 50
    CONST val 240          ; Vertegenwoordigt het getal 2.40 (240 / 100)
    CONST factor 150       ; Vertegenwoordigt het getal 1.50 (150 / 100)

    MACRO scale(reg, scale) {
        MULI reg scale
    }  

    MACRO dscale(reg, scale) {
        DIVI reg scale
    }

    ; Correcte Fixed-Point Vermenigvuldigingsmacro: Rx = (Rx * Ry) / scale
    MACRO fmul(Rx, Ry, scale) {
        MUL Rx, Ry
        DIVI Rx, scale
    }

    ; Fixed-Point Vermenigvuldigingsmacro met Round-to-Nearest afronding
    MACRO fmul_round(Rx, Ry, scale, half) {
        MUL Rx, Ry
        ADDI Rx, half
        DIVI Rx, scale
    }

    ; MACRO fdiv(Rx, denominator, scale)
    ; Berekent: Rx = (Rx * scale) / denominator
    MACRO fdiv(Rx, denominator, scale) {
        MULI Rx, scale
        DIV Rx, denominator
    }


}

PROGRAM {
main:
    0 -> I
    0 -> C

    ; --- Stap 1: Laad initiële waarde (2.40) en sla op ---
    val -> A                ; A = 240 (2.40)
    A -> [result + I]       ; Opslaan op result[0]
    INC I                   ; Index I = 1

    ; --- Stap 2: Voer schalingstests uit conform oorspronkelijk script ---
    scale(A, FP-scale)      ; A = 240 * 100 = 24000
    A -> [result + I]       ; Opslaan op result[1]
    INC I                   ; Index I = 2

    dscale(A, FP-scale)     ; A = 24000 / 100 = 240
    A -> [result + I]       ; Opslaan op result[2]
    INC I                   ; Index I = 3

    ; --- Stap 3: Correcte Fixed-Point Vermenigvuldiging (2.40 * 1.50 = 3.60) ---
    factor -> B             ; B = 150 (1.50)
    fmul(A, B, FP-scale)    ; A = (240 * 150) / 100 = 36000 / 100 = 360 (3.60)
    A -> [result + I]       ; Opslaan op result[3]
    INC I

    ; === test stap 4
    val -> A
    factor -> B 
    fmul_round(A, B, FP-scale, FP-half)
    A -> [result + I]
    INC I

    ; === test step 5 division
    val -> A
    factor -> B 
    fdiv(A, B, FP-scale)
    A -> [result + I]
    INC I


    ; === test step 6
    1 -> A
    scale(A, 1000)
    3 -> B
    scale(B, 1000)

    fdiv(A, B, 1000)
    A -> [result + I]
    INC I

    A -> C
    fmul(A, B, 1000)
    A -> [result + I]
    INC I


    C -> A
    fmul_round(A, B, 1000, 500)
    A -> [result + I]
    INC I
    
    ; === test step 7: Toon het nut van fmul_round
    ; Berekening: 1.50 * 1.35 (150 * 135)
    150 -> A
    135 -> B

    ; Zonder afronding
    fmul(A, B, 100)
    A -> [result + I]       ; Geeft 202 (2.02) -> Fout door afkapping
    INC I

    150 -> A
    135 -> B

    ; Mét afronding
    fmul_round(A, B, 100, 50)
    A -> [result + I]       ; Geeft 203 (2.03) -> Wiskundig correct!
    INC I

    HALT
}