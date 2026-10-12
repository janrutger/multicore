MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === GEHEUGEN ALLOCATIE (UNIVERSUM STATE) ===
    CONST NUM_BODIES 64        ; Totaal 24 hemellichamen
    SHARED body_x 64           ; Actuele X-posities
    SHARED body_y 64           ; Actuele Y-posities
    SHARED body_vx 64          ; Snelheid X
    SHARED body_vy 64          ; Snelheid Y

    ; Synchronisatie en slot-status voor de lichamen
    SHARED body_status 64      ; 0 = Vrij/Klaar, 1 = Bezig met berekenen (Worker lock)
    SHARED step_counter 1      ; Huidige simulatieronde

    CONST MAX_STEPS 600        ; Aantal simulatieframes

    ; Schermmidden (uitgaande van 640x480 resolutie)
    CONST CENTER_X 320
    CONST CENTER_Y 240

    ; Fixed-Point Schaal
    CONST FP_SCALE 1000
    CONST FP_HALF 500

    ; I/O Poorten voor GraphicalDisplay
    IO DEV 0
    IO VAL 1
    IO X_POS 2
    IO Y_POS 3
    IO CMD 5

    CONST GRAPH_DEV 2
    CONST PLOT_CMD 2
    CONST CLR_CMD 3

    ; === MACRO'S ===
    MACRO startTask(task, arg) {
        _spawntask:
            RCONTEXT arg task        ; Probeer remote worker via CIU (Link 0 t/m 3)
            SUCCES _spawnd

            CONTEXT arg task         ; Fallback: lokaal op CPU 0
            SUCCES _spawnd

            JMP _spawntask           ; Wacht tot er een core vrij komt
        _spawnd:
    }
}

PROGRAM {

; ==========================================================
; DOMEIN 1: CPU 0 (MASTER COORDINATOR & DISPLAY RENDERER)
; ==========================================================
main:
    0 -> A
    0 -> I
    0 -> B
    0 -> K

    ; 1. Initialiseer GraphicalDisplay bus op CPU 0
    GRAPH_DEV -> A
    OUT A DEV

    ; 2. Initialiseer beginposities en snelheden generiek rondom het schermmidden met grotere spreiding
    0 -> I
    INIT_LOOP:
        ; --- X-POSITIE BEREKENING (Brede spreiding rond CENTER_X) ---
        I -> A
        5 -> B
        MOD A, B           ; A = I % 5 (geeft 0 t/m 4)
        40 -> B            ; Grotere stapgrootte (was 8)
        MUL A, B           ; A = (I % 5) * 40
        80 -> B            ; Helft van het bereik om te centreren (was 16)
        SUB A, B           ; A = offset (-80 tot +80)
        CENTER_X -> B
        ADD A, B           ; A = CENTER_X + offset
        A -> [body_x + I]  ; Sla op in shared RAM

        ; --- Y-POSITIE BEREKENING (Brede spreiding rond CENTER_Y) ---
        I -> A
        7 -> B
        MOD A, B           ; A = I % 7 (geeft 0 t/m 6)
        30 -> B            ; Grotere stapgrootte (was 8)
        MUL A, B           ; A = (I % 7) * 30
        90 -> B            ; Helft van het bereik om te centreren (was 16)
        SUB A, B           ; A = offset (-90 tot +90)
        CENTER_Y -> B
        ADD A, B           ; A = CENTER_Y + offset
        A -> [body_y + I]  ; Sla op in shared RAM

        ; --- SNELHEID VX BEREKENING ---
        I -> A
        3 -> B
        MOD A, B           ; A = I % 3
        1 -> B
        SUB A, B           ; A = (I % 3) - 1 (-1, 0, 1)
        A -> [body_vx + I]

        ; --- SNELHEID VY BEREKENING ---
        I -> A
        1 -> B
        ADD A, B           ; A = I + 1
        3 -> B
        MOD A, B           ; A = (I + 1) % 3
        1 -> B
        SUB A, B           ; A = ((I + 1) % 3) - 1 (-1, 0, 1)
        A -> [body_vy + I]

        ; --- VOLGENDE LICHAAM ---
        INC I
        NUM_BODIES -> B
        IF (I == B) FALSE {
            JMP INIT_LOOP
        }

    MAX_STEPS -> A
    A -> [step_counter]

; --- MASTER RENDER & SIMULATIE STURINGSLUS ---
SIMULATION_TICK:
    0 -> I
    TICK_LOOP:
        startTask(BODY_SIMULATE, I)

        INC I
        NUM_BODIES -> B
        IF (I == B) FALSE {
            JMP TICK_LOOP
        }

    WAIT_FOR_CONTEXTEN:
        ALLSYNC WAIT_FOR_CONTEXTEN

    ; CLEAR screen voor het nieuwe frame
    CLR_CMD -> A 
    OUT A CMD
    IOSYNC

    0 -> I
    DRAW_LOOP:
        12 -> A
        OUT A VAL
        [body_x + I] -> A
        OUT A X_POS
        [body_y + I] -> A
        OUT A Y_POS
        PLOT_CMD -> A
        OUT A CMD
        IOSYNC

        INC I
        NUM_BODIES -> B
        IF (I == B) FALSE {
            JMP DRAW_LOOP
        }

    [step_counter] -> A
    DEC A
    A -> [step_counter]
    TSTZ A
    JMPF SIMULATION_TICK

    HALT

; ==========================================================
; DOMEIN 3: uCore SUB-CONTEXT (ZWAARTEKRACHT & POSITIE UPDATE)
; Input: Register I bevat het Lichaam ID (0 t/m 23)
; ==========================================================
BODY_SIMULATE:
    0 -> B
    0 -> C
    0 -> L
    0 -> M

    ; 1. Lees huidige positie en snelheid
    LDX A, body_x            ; A = X
    LDX B, body_vx           ; B = VX
    LDX C, body_y            ; C = Y
    LDX K, body_vy           ; K = VY

    ; Laad de schermmidden coördinaten voor de zwaartekrachtrekening
    CENTER_X -> L
    CENTER_Y -> M

    ; 2. Centrale zwaartekracht naar het nieuwe middelpunt (CENTER_X, CENTER_Y)
    IF (A > L) FALSE {
        INC B
    }
    IF (A > L) TRUE {
        DEC B
    }
    IF (C > M) FALSE {
        INC K
    }
    IF (C > M) TRUE {
        DEC K
    }

    ; Sla nieuwe snelheid op
    STX B, body_vx
    STX K, body_vy

    ; 3. Pas snelheid toe op positie
    ADD A, B                 ; X = X + VX
    ADD C, K                 ; Y = Y + VY

    ; Sla nieuwe posities op in Shared RAM
    STX A, body_x
    STX C, body_y

    AUTOCLOSE



; ==========================================================
; DOMEIN 3: uCore SUB-CONTEXT (N-BODY UNIVERSELE ZWAARTEKRACHT)
; Input: Register I bevat het Lichaam ID (0 t/m NUM_BODIES-1)
; ==========================================================
BODY_SIMULATE_new:
    ; 1. Parkeer het eigen Lichaam ID veilig (omdat I gebruikt wordt voor LDX/STX)
    0 -> Y
    I -> Y                  ; Y = mijn eigen Lichaam ID backup

    0 -> B                  ; Delta VX accumulator
    0 -> C                  ; Delta VY accumulator
    0 -> L                  ; Inner-loop teller L = 0
    0 -> M 
    NUM_BODIES -> X         ; Totaal aantal lichamen
    0 -> Z 

    ; Lees eigen positie van lichaam I uit Shared RAM (gebruikt huidige I)
    LDX A, body_x           ; A = mijn X
    LDX K, body_y           ; K = mijn Y

    ; Bewaar eigen posities tijdelijk in registers om conflicten te vermijden
    A -> M                  ; M = mijn X-backup
    K -> Z                  ; Z = mijn Y-backup

    ; --- 2. DE GENESTE INTERACTIE-LUS (L van 0 tot NUM_BODIES) ---
N_BODY_LOOP:
    ; Check of L gelijk is aan ons eigen ID (geen zelf-aantrekking)
    TSTE L Y                ; Vergelijk lus-teller L met onze opgeslagen ID in Y
    JMPT _skip_self         ; Als L == Y, sla deze iteratie over

    ; Lees positie van het andere lichaam L via de compiler-ondersteunde indexering
    [body_x + L] -> A       ; A = X van lichaam L
    [body_y + L] -> K       ; K = Y van lichaam L

    ; Bereken afstandsdeltas: dx = body_x[L] - body_x[I]
    SUB A, M                ; A = X_l - X_i (dx)
    SUB K, Z                ; K = Y_l - Y_i (dy)

    ; Accumuleer de krachten (eenvoudige lineaire krachtsopbouw als start)
    ADD B, A                ; Accumuleer dx in B
    ADD C, K                ; Accumuleer C in K

_skip_self:
    INC L                   ; Verhoog inner-loop teller L
    TSTE L X                ; Is L gelijk aan NUM_BODIES?
    JMPF N_BODY_LOOP        ; Zo niet, spring terug naar het begin van de lus

    ; --- 3. HERSTEL EIGEN ID EN PAS SNELHEID/POSITIE TOE ---
    Y -> I                  ; Herstel het originele Lichaam ID in I voor de LDX/STX commando's

    ; Lees huidige snelheid van lichaam I
    LDX A, body_vx          ; A = VX
    LDX K, body_vy          ; K = VY

    ; Tel de opgebouwde gravitatie-invloeden op bij de snelheid
    ADD A, B                ; Nieuwe VX = VX + Delta_VX
    ADD K, C                ; Nieuwe VY = VY + Delta_VY

    ; Sla de nieuwe snelheid op in Shared RAM
    STX A, body_vx
    STX K, body_vy

    ; 4. Pas snelheid toe op de actuele positie
    LDX A, body_x           ; Haal huidige X op
    LDX C, body_y           ; Haal huidige Y op
    ADD A, B                ; X = X + VX
    ADD C, K                ; Y = Y + VY

    ; Sla de nieuwe posities op in Shared RAM
    STX A, body_x
    STX C, body_y

    AUTOCLOSE
}
