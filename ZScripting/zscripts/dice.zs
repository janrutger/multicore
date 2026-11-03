MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; Reserveer shared geheugenruimte voor de tellers van oog 1 t/m 6
    SHARED count1 1     ; Adres 1024
    SHARED count2 1     ; Adres 1025
    SHARED count3 1     ; Adres 1026
    SHARED count4 1     ; Adres 1027
    SHARED count5 1     ; Adres 1028
    SHARED count6 1     ; Adres 1029

    CONST rnd_seed 421  ; Start-seed voor de generator
    CONST modulo_val 6  ; Aantal zijden van de dobbelsteen
    CONST max_rolls 2000 ; Aantal worpen

    PRIVATE SEED 1
    MACRO rand(val, size) {
        LDM val SEED       ; 1. Laad de huidige state vanuit private geheugen
        RND32 val 21       ; 2. Update naar het volgende 32-bits random getal
        STO val SEED       ; 3. Sla de nieuwe state direct weer veilig op
        SHIFTR val size    ; 4. Pas de schaling toe op de werkwaarde
    }
}

PROGRAM {
main:
    0 -> A
    0 -> B

    0 -> K
    0 -> M
    0 -> X
    0 -> Z

    ; --- INITIALISATIE ---
    LDI K, rnd_seed     ; K fungeert als onze PRNG state-register
    STO K SEED
    LDI X, max_rolls    ; X is onze lus-teller (100 worpen)
    LDI Z, 0            ; Z blijft vast op 0 voor vergelijkingen

DICE_LOOP:
    ; 1. Genereer een nieuw willekeurig 32-bit getal via onze uCore instructie
    ; RND32 K, 21       ; Update de state in K met onze robuuste mix


    ; 2. Bereken de dobbelsteen-waarde (Rando_getal % 6)
    ; We kopiëren K naar A, en passen MOD toe met de constante 6
    ; LD A, K
    ; SHIFTR A, 24        ; Schuif 24 bits naar rechts -> houdt een klein 8-bit getal over (0 t/m 255)!

    rand(A, 24)
    modulo_val -> M 
    MOD A, M   ; A = A % 6 (resulteert in 0, 1, 2, 3, 4 of 5)

    ; 3. Verhoog de juiste frequentie-teller in het shared geheugen
    ; We kunnen hier een schone if/else of conditional check gebruiken per oog, 
    ; of direct adresseren. Laten we een snelle reeks checks doen:

    LDI B, 0
    TSTE A, B           ; Is het oog 0? (komt overeen met dobbelsteen 1)
    JMPF CHECK_TWO
    LDM B, count1
    INC B
    STO B, count1
    JMP NEXT_ROLL

CHECK_TWO:
    LDI B, 1
    TSTE A, B           ; Is het oog 1? (dobbelsteen 2)
    JMPF CHECK_THREE
    LDM B, count2
    INC B
    STO B, count2
    JMP NEXT_ROLL

CHECK_THREE:
    LDI B, 2
    TSTE A, B           ; Is het oog 2? (dobbelsteen 3)
    JMPF CHECK_FOUR
    LDM B, count3
    INC B
    STO B, count3
    JMP NEXT_ROLL

CHECK_FOUR:
    LDI B, 3
    TSTE A, B           ; Is het oog 3? (dobbelsteen 4)
    JMPF CHECK_FIVE
    LDM B, count4
    INC B
    STO B, count4
    JMP NEXT_ROLL

CHECK_FIVE:
    LDI B, 4
    TSTE A, B           ; Is het oog 4? (dobbelsteen 5)
    JMPF CHECK_SIX
    LDM B, count5
    INC B
    STO B, count5
    JMP NEXT_ROLL

CHECK_SIX:              ; Alles wat overblijft (oog 5) is dobbelsteen 6
    LDM B, count6
    INC B
    STO B, count6

NEXT_ROLL:
    ; 4. Lus-beheer: verlaag teller X en herhaal tot 100 worpen bereikt zijn
    DEC X
    TSTZ X
    JMPF DICE_LOOP      ; Als X nog niet 0 is, gooi opnieuw!


END_RUN:
    HALT                ; Klaar! Bekijk de geheugendump van 1024 t/m 1029.
}