MAP {
    MEMSIZE 1024
    START main

    RES INbuffer 16

    CONST devicetype 1      ; CHAR device
    CONST instructie 1      ; PRINT
    IO DEV 0
    IO VAL 1
    IO CMD 5
    IO KBD 6


    MACRO PRTchar(dev, cmd, reg) {
        LDI K dev
        LDI L cmd
        OUT K DEV
        OUT reg VAL
        OUT L CMD

        IOSYNC

    }


    MACRO KBDread(reg_target) {
    POLL_LUS:
        IOSYNC              ; Geef de controller een kloktik om de KBD-buffer te vullen
        IN reg_target KBD   ; Haal de status/toets op uit reg6
        LDI K 0
        TSTZ reg_target     ; Is het 0? (Geen input)
        JMPT POLL_LUS       ; Ja? Blijf pollen tot er een toets is!
    }


} ; Einde MAP



PROGRAM {
main:
    LDI I 0             ; Initialiseer index-register voor buffer
    LDI B 27            ; ESC ascii

    REPEAT UNTIL (A == B) {
        KBDread(A)      ; Macro-call voor IN A 6 etc.
        STX A INbuffer  
        INC I               
        PRTchar(devicetype, instructie, A)      ; Macro-call voor echo console
    } 

end_program:
    HALT
}