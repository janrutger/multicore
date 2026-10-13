MAP {
    MEMORY {
        PROGRAM 1024
        SHARED  1024
        PRIVATE 512
    }
    START main

    ; === GEHEUGEN ALLOCATIE (UNIVERSUM STATE) ===
    CONST NUM_BODIES 16        ; Totaal 24 hemellichamen
    SHARED body_x 16           ; Actuele X-posities
    SHARED body_y 16           ; Actuele Y-posities
    SHARED body_vx 16          ; Snelheid X
    SHARED body_vy 16          ; Snelheid Y

    ; Synchronisatie en slot-status voor de lichamen
    SHARED body_status 16      ; 0 = Vrij/Klaar, 1 = Bezig met berekenen (Worker lock)
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
        startTask(BODY_SIMULATE_new, I)

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
    ; 1. Bewaar het eigen ID in register M
    0 -> M
    I -> M                  ; M = mijn eigen Lichaam ID backup

    0 -> A 
    0 -> B 
    0 -> C 

    0 -> X                  ; Accumulator Delta VX = 0
    0 -> Y                  ; Accumulator Delta VY = 0
    0 -> L                  ; Inner-loop teller L = 0

    ; Lees eigen positie uit Shared RAM
    LDX A, body_x           ; A = mijn X
    LDX K, body_y           ; K = mijn Y

    ; Bewaar eigen posities tijdelijk in registers
    A -> B                  ; B = mijn X-backup
    K -> C                  ; C = mijn Y-backup

    NUM_BODIES -> Z         ; Z = Totaal aantal lichamen

; --- 2. DE GENESTE INTERACTIE-LUS ---
N_BODY_LOOP:
    ; Check of L gelijk is aan ons eigen ID (M)
    TSTE L M
    JMPT _skip_self

    ; Lees positie van het andere lichaam L
    [body_x + L] -> A       ; A = X van lichaam L
    [body_y + L] -> K       ; K = Y van lichaam L

    ; Bereken afstandsdeltas: dx = body_x[L] - body_x[I]
    SUB A, B                ; A = dx (X_l - X_i)
    SUB K, C                ; K = dy (Y_l - Y_i)

    ; Schaal de zwaartekracht flink af (delen door 32) om rustige banen te krijgen
    DIVI A, 32
    DIVI K, 32

    ; Accumuleer deltas in X en Y
    ADD X, A                ; X = X + dx
    ADD Y, K                ; Y = Y + dy

_skip_self:
    INC L                   ; Volgende lichaam
    TSTE L Z                ; Is L == NUM_BODIES?
    JMPF N_BODY_LOOP        ; Zo niet, herhaal

    ; --- 3. HERSTEL EIGEN ID EN PAS SNELHEID TOE ---
    M -> I                  ; Herstel origineel ID in I

    ; Lees huidige snelheid
    LDX A, body_vx          ; A = VX
    LDX K, body_vy          ; K = VY

    ; DEMPING (Wrijving tegen oneindig doorschieten)
    SHIFTR A, 1             ; VX = VX / 2
    SHIFTR K, 1             ; VY = VY / 2

    ; Tel de geaccumuleerde N-body krachten op
    ADD A, X                ; VX += Delta_VX
    ADD K, Y                ; VY += Delta_VY

    ; === EXTRA: Lichte trekkracht naar het schermmidden (CENTER_X / CENTER_Y) ===
    LDX B, body_x           ; B = Huidige X
    CENTER_X -> Z
    SUB Z, B                ; Z = CENTER_X - X
    DIVI Z, 64              ; Zachte trekkracht
    ADD A, Z                ; Tel toe aan VX

    LDX C, body_y           ; C = Huidige Y
    CENTER_Y -> Z
    SUB Z, C                ; Z = CENTER_Y - Y
    DIVI Z, 64              ; Zachte trekkracht
    ADD K, Z                ; Tel toe aan VY
    ; =========================================================================

    ; Sla de nieuwe snelheden op
    STX A, body_vx
    STX K, body_vy

    ; --- 4. PAS SNELHEID TOE OP POSITIE ---
    ADD B, A                ; Nieuwe X = X + VX
    ADD C, K                ; Nieuwe Y = Y + VY

    STX B, body_x
    STX C, body_y

    AUTOCLOSE

}