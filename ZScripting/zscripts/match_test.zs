MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; Test-constante en resultaten-buffer in Private RAM
    CONST SPECIAL_VAL 42
    SHARED results 6
}

PROGRAM {

main:
    ; We slaan de uitkomst van elke test op in array 'results[0..5]'
    ; Verwachte eindwaarden in geheugen: [10, 20, 30, 99, 55, 77]

    ; ==========================================================
    ; TEST 1: Waarde-match (0 ->)
    ; ==========================================================
    0 -> A
    MATCH A {
        0 -> {
            10 -> B
            B -> [results]          ; Verwacht: 10
        }
        SPECIAL_VAL -> {
            999 -> B
            B -> [results]
        }
        DEFAULT -> {
            888 -> B
            B -> [results]
        }
    }

    ; ==========================================================
    ; TEST 2: Constante match (SPECIAL_VAL ->)
    ; ==========================================================
    42 -> A
    1 -> I
    MATCH A {
        0 -> {
            999 -> B
            B -> [results + I]
        }
        SPECIAL_VAL -> {
            20 -> B
            B -> [results + I]      ; Verwacht: 20
        }
        DEFAULT -> {
            888 -> B
            B -> [results + I]
        }
    }

    ; ==========================================================
    ; TEST 3: Hybride Guard in MATCH ((C > B) TRUE ->)
    ; ==========================================================
    99 -> A
    10 -> B
    50 -> C
    0 -> M
    2 -> I
    MATCH A {
        0 -> {
            999 -> M
            M -> [results + I]
        }
        (C > B) TRUE -> {
            30 -> M
            M -> [results + I]      ; Verwacht: 30 (want 50 > 10)
        }
        DEFAULT -> {
            888 -> M
            M -> [results + I]
        }
    }

    ; ==========================================================
    ; TEST 4: DEFAULT Fallback (geen enkele match)
    ; ==========================================================
    7 -> A
    3 -> I
    MATCH A {
        0 -> {
            999 -> B
            B -> [results + I]
        }
        1 -> {
            888 -> B
            B -> [results + I]
        }
        DEFAULT -> {
            99 -> B
            B -> [results + I]      ; Verwacht: 99
        }
    }

    ; ==========================================================
    ; TEST 5: Zonder DEFAULT (moet netjes doorlopen)
    ; ==========================================================
    55 -> B
    4 -> I
    5 -> A
    MATCH A {
        1 -> {
            999 -> B
        }
        2 -> {
            888 -> B
        }
    }
    B -> [results + I]              ; Verwacht: 55 (onaangetast gebleven)

    ; ==========================================================
    ; TEST 6: Targetless MATCH (pure conditionele guards met FALSE)
    ; ==========================================================
    15 -> X
    5 -> I
    MATCH {
        (X ZERO) TRUE -> {
            999 -> B
            B -> [results + I]
        }
        (X == B) FALSE -> {
            77 -> B
            B -> [results + I]      ; Verwacht: 77 (want 15 != 55)
        }
    }

    HALT
}