MAP {
    MEMSIZE 1024
    START main

    RES INbuffer 16
    RES ENCODEbuffer 16

    CONST masterkey 13
    CONST chars 1      
    CONST print 1      
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
    POLL_LUS:
        IOSYNC
        IN reg_target KBD
        TSTZ reg_target
        JMPT POLL_LUS
    }
}

PROGRAM {
main:
    0  -> I            ; Teller voor toetsenbord-invoer
    27 -> B            ; ESC ascii stop-teken

    REPEAT UNTIL (A == B) {
        KBDread(A)      
        A -> [INbuffer + I]
        INC I               
        PRTchar(chars, print, A)      
    } 

    ; --- DE NIEUWE PARALLEL ABSTRACTIE ---
    ; X en Y worden gebruikt als onafhankelijke streaming pointers.
    0 -> X             ; Read pointer voor INbuffer
    0 -> Y             ; Write pointer voor ENCODEbuffer

    PARALLEL (XOR_WORKER) USING [INbuffer + X] UNTIL (A == B) {
        A -> [ENCODEbuffer + Y]
    }

end_program:
    HALT
    

XOR_WORKER:
    LDI K, 7
    SM32_RND A, 7       ; Brute hardware-shuffle (mix met shift en rotatie!)
    XOR A, K            ; XOR de boel
    CLOSE               ; Geef uCore vrij aan de master met status VALID
}