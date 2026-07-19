MAP {
    MEMSIZE 1024
    START main

    RES INbuffer 16
    RES ENCODEbuffer 16

    CONST masterkey 13

    CONST chars 1      ; CHAR device
    CONST print 1      ; PRINT
    IO DEV 0
    IO VAL 1
    IO CMD 5
    IO KBD 6


    MACRO PRTchar(dev, cmd, reg) {
        dev -> K
        cmd -> L
        OUT K DEV
        OUT reg VAL
        OUT L CMD
        IOSYNC
    }


    MACRO KBDread(reg_target) {
    POLL_LUS:               ; gaat dus niet stuk met commentaar
        IOSYNC              ; Geef de controller een kloktik om de KBD-buffer te vullen
        IN reg_target KBD   ; Haal de status/toets op uit reg6
        TSTZ reg_target     ; Is het 0? (Geen input)
        JMPT POLL_LUS       ; Ja? Blijf pollen tot er een toets is!
    }


} ; Einde MAP



PROGRAM {
main:
    0  -> I            ; Initialiseer index-register voor compiler gebruik 
    27 -> B             ; ESC ascii

    REPEAT UNTIL (A == B) {
        KBDread(A)      ; Macro-call voor IN A 6 etc.
        A -> [INbuffer + I]
        INC I               
        PRTchar(chars, print, A)      ; Macro-call voor echo console
    } 

; Lees de karaters terug een Start een context
; die een XOR met de masterkey uitvoerd
; bij terugkeer wordt de nieuwe waarde weg geschreven

    0 -> X          ; read buffer pointer
    0 -> Y          ; writebuffer pointer

    LOOP:
        [INbuffer + X] -> A
        TSTE A B
        JMPT oogst_laatsten
        

        CONTEXT A XOR_WORKER
        FAIL oogst
        INC X 

        JOIN A LOOP
        A -> [ENCODEbuffer + Y]
        INC Y

        JMP LOOP


    oogst:
        JOIN A oogst
        A -> [ENCODEbuffer + Y]
        INC Y

        JMP LOOP


    oogst_laatsten:
        JOIN A klaar
        A -> [ENCODEbuffer + Y]
        INC Y
        JMP oogst_laatsten

    klaar:
        SYNC oogst_laatsten
        B -> [ENCODEbuffer + Y]



end_program:
    HALT

XOR_WORKER:
    masterkey -> K

    XOR A K

    CLOSE
    ; RETURN A
}