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

    MACRO KBDread(reg_target) {
    POLL_LUS:
        IOSYNC              
        IN reg_target KBD   
        TSTZ reg_target     
        JMPT POLL_LUS       
    }

    MACRO PRTchar(dev, cmd, reg) {
        dev -> K
        cmd -> L
        OUT K DEV
        OUT reg VAL
        OUT L CMD
        IOSYNC
    }
}

PROGRAM {
main:
    0  -> I            
    27 -> B            ; ESC ascii code

    REPEAT UNTIL (A == B) {
        KBDread(A)
        A -> [INbuffer + I]
        INC I    
        PRTchar(chars, print, A)      ; Macro-call voor echo console           
    } 

    0 -> X          ; Read buffer pointer
    0 -> Y          ; Write buffer pointer

    [INbuffer + X] -> A

    ; ==========================================================
    ;  SPAWN PIJPLIJN 1 (Met een geneste IF in het HARVEST blok!)
    ; ==========================================================
    SPAWN XOR_WORKER A UNTIL (A == B) TRUE UPDATE {
        INC X
        [INbuffer + X] -> A
    } HARVEST C {
        ; IF-statement binnen HARVEST om unieke site-tagging te testen!
        IF (C ZERO) FALSE {
            C -> [ENCODEbuffer + Y]
            INC Y
        }
    }

    ; ==========================================================
    ;  SPAWN PIJPLIJN 2 (Proeft op unieke spawn_id labels!)
    ; ==========================================================
    0 -> X
    0 -> Y
    [INbuffer + X] -> A

    SPAWN XOR_WORKER A UNTIL (A == B) TRUE UPDATE {
        INC X
        [INbuffer + X] -> A
    } HARVEST C {
        C -> [ENCODEbuffer + Y]
        INC Y
    }

    B -> [ENCODEbuffer + Y]
    HALT

XOR_WORKER:
    masterkey -> K
    0 -> C
    XOR A K
    A -> C
    MUL A C
    CLOSE
}