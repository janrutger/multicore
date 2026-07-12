# opcodes.py
from enum import IntEnum

class Op(IntEnum):
    # --- FORMAT: ZERO ---
    NOP   = 10
    HALT  = 11      # Implemented
    IOSYNC= 12      # NEW: Non-blocking tick voor de IO-controller
    # RET   = 12
    # EI    = 13
    # DI    = 14
    # RTI   = 15

    CLOSE = 29      # Implemented

    # --- FORMAT: ONE_ADDR ---
    JMPF  = 20      # Implemented
    JMPT  = 21      # Implemented
    JMP   = 22      # Implemented
    # CALL  = 24
    # CALLX = 25
    # INT   = 26

    SUCCES = 16      # Implemented
    FAIL   = 17      # Implemented
    SYNC   = 18      # Implemented

    # --- FORMAT: TWO_REG_VAL / TWO_REG_ADDR --- 
    LDI   = 31      # Implemented
    LDM   = 32      # Implemented
    LDX   = 33      # Implemented
    OUT   = 34      # NEW: Schrijf register Rx naar IO reg#
    IN    = 35      # NEW: Lees IO reg# naar register Rx
    STO   = 40      # Implemented
    STX   = 41      # Implemented
    ADDI  = 51
    SUBI  = 53
    MULI  = 61
    DIVI  = 63
    TST   = 70
    ANDI  = 82
    # STACK = 92
    # USTACK= 93

    CONTEXT = 27      # Implemented
    JOIN    = 28      # Implemented

    SHIFTL   = 43      # Implemented
    ROTL32   = 44      # Implemented
    SM32_RND = 45      # Implemented

    # --- FORMAT: TWO_REG_REG ---
    LD    = 30      # Implemented 
    ADD   = 50      # Implemented 
    SUB   = 52
    MUL   = 60      # Implemented
    MOD   = 65      # Implemented
    TSTE  = 71      # Implemented
    TSTG  = 72

    XOR    = 42     # Implemented
    

    # --- FORMAT: ONE_REG ---
    # PUSH  = 90
    # POP   = 91
    # GPU   = 94
    # CALLS = 95
    INC   = 80     # Implemented
    DEC   = 81     # Implemented
    RETURN= 19    # Implemented

# Vaste sets voor de decoder om snel het format te matchen
FORMAT_ZERO        = {Op.NOP, Op.HALT, Op.CLOSE, Op.IOSYNC}
FORMAT_ONE_ADDR    = {Op.JMPF, Op.JMPT, Op.JMP, Op.SUCCES, Op.FAIL, Op.SYNC}
FORMAT_ONE_REG     = {Op.INC, Op.DEC, Op.RETURN}
FORMAT_TWO_REG_REG = {Op.LD, Op.ADD, Op.SUB, Op.MUL, Op.MOD, Op.TSTE, Op.TSTG, Op.XOR}
FORMAT_TWO_REG_VAL = {
    Op.LDI, Op.LDM, Op.LDX, Op.OUT, Op.IN, Op.STO, Op.STX, 
    Op.SHIFTL, Op.ROTL32, Op.SM32_RND, Op.CONTEXT, Op.JOIN, 
    Op.ADDI, Op.SUBI, Op.MULI, Op.DIVI, Op.TST, Op.ANDI
}


class Reg(IntEnum):
    I  = 0  # Index Register (Vaste hardware-koppeling voor LDX/STX)
    A  = 1  # Accumulator / Algemeen register 1
    B  = 2  # Algemeen register 2
    C  = 3  # Algemeen register 3
    K  = 4  # Algemeen register 4
    L  = 5  # ... enzovoorts tot R9 ...
    M  = 6
    X  = 7
    Y  = 8
    Z  = 9





# ucode instructions rom
# ucode instruction map to ucore primitives
# ucode instructions are called by de CPU intructionn(dispatch)
MICROCODE_ROM = {
    'ldv':    ['mv_tv',  'setResult'],
    'ld':     ['valid_v', 'valid_w', 'mv_wv', 'setResult'],
    'stv':    ['mv_vt',  'setResult'],
    'status': ['status', 'setResult'],

    'add':    ['valid_v', 'valid_w', 'add', 'setResult'],
    'sub':    ['valid_v', 'valid_w', 'sub', 'setResult'],
    'mul':    ['valid_v', 'valid_w', 'mul', 'setResult'],
    'div':    ['valid_v', 'valid_w', 'div', 'setResult'],

    'inc':    ['valid_v', 'inc_v', 'setResult'],
    'dec':    ['valid_v', 'dec_v', 'setResult'],

    'tstz':   ['valid_v', 'tstz', 'setResult'],
    'tstn':   ['valid_v', 'tstn', 'setResult'],

    'cmpe':   ['valid_v', 'valid_w', 'cmpe',  'setResult'],
    'cmpne':  ['valid_v', 'valid_w', 'cmpne', 'setResult'],
    'cmpgt':  ['valid_v', 'valid_w', 'cmpgt', 'setResult'],
    'cmplt':  ['valid_v', 'valid_w', 'cmplt', 'setResult'],

    'xor_vw': ['valid_v', 'valid_w', 'xor_vw',   'setResult'],
    'shftl':  ['valid_v', 'mv_tw',   'shftl_vw', 'setResult'],
    'rol32':  ['valid_v', 'mv_tw',   'rol32_vw', 'setResult'],


   'slow_mul': [
        'valid_v',             # 0: Wacht op A en onthoud teken
        'valid_w',             # 1: Wacht op B en onthoud teken
        'abs_v',               # 2: Maak V positief voor de lus
        'abs_w',               # 3: Maak W positief voor de lus
        
        # --- SWAP OPTIMALISATIE ---
        'cmplt',               # 4: Is V < W?
        ('bra_true', 4),       # 5: JA? Sla de swap over! Spring +4 verder -> naar clr_t (index 9)
        'mv_vt',               # 6: T = V
        'mv_wv',               # 7: V = W (V is nu de kleinste teller!)
        'mv_tw',               # 8: W = T (W is nu de grootste opteller!)
        
        # --- DE LUS ---
        'clr_t',               # 9: T = 0 (Reset accumulator)
        'tstz',                # 10: Is V == 0?
        ('bra_true', 4),       # 11: JA? Lus klaar! Spring +4 verder -> naar mv_tv (index 15)
        'add_tw',              # 12: T = T + W
        'dec_v',               # 13: V = V - 1
        ('bra_always', -4),    # 14: Spring -4 terug -> naar tstz (index 10)
        
        # --- AFRONDING ---
        'mv_tv',               # 15: Zet het positieve resultaat uit T terug in V
        'sign_vxor',           # 16: Pas het onthouden teken toe op V via XOR!
        'setResult'            # 17: Meld aan de CPU dat de core VALID is
    ],

    'mod' : [
        'valid_v',         # 0: Vacht op invoer V (het grote getal komt in self.value)
        'valid_w',         # 1: Wacht op invoer W (de deler komt in self.work)
        
        # --- HOOFD GUARD: CHECK DELER OP 0 (Puur intern!) ---
        'mv_vt',           # 2: T = V (Sla het grote getal VEILIG op in kluis T)
        'mv_wv',           # 3: V = W (Zet de deler W tijdelijk in V om te kunnen testen)
        'tstz',            # 4: Is V (de deler) gelijk aan 0?
        ('bra_true', 8),   # 5: JA? De deler is 0! Spring direct naar setResult (+8 -> index 13)
        
        # --- NOPE? HERSTEL V EN REKEN-SAFE MAKEN ---
        'mv_tv',           # 6: V = T (Haal het grote getal weer onbeschadigd uit kluis T)
        'abs_v',           # 7: Maak V positief (signed arithmetic safe)
        'abs_w',           # 8: Maak W positief
        
        # --- DE VEILIGE MODULO LUS ---
        'cmplt',           # 9:  self.status = (self.value < self.work)
        ('bra_true', 3),   # 10: JA? Klaar! Spring +3 naar setResult (index 13)
        'sub',             # 11: self.value = self.value - self.work
        ('bra_always', -3),# 12: Spring -3 terug naar cmplt (index 9)
        
        'setResult'        # 13: Meld aan de CPU dat we VALID zijn
    ],


    'sm32_rnd': [
        'valid_v',         # 0: Wacht op invoer V
        'mv_tw',           # 1: Laad de immediate integer (bijv. 7) in W
        
        # --- HARDWARE SHUFFLE ---
        #'shftl_vw',        # 2: V = V << W (Shift de sleutel met 7)
        'rol32_vw', 
        'add',             # 3: V = V + W  (Tel de mixer-waarde 7 erbij op)
        'rol32_vw',        # 4: V = V ROL32 W (Roteer het resultaat nogmaals met 7)
        
        'setResult'        # 5: Klaar!
    ],
}








encrypt_program = """
    LDI M 287454020           ; Value of the master key
    STO M 512           ; Store masterkey at 512

    ; ==========================================================
    ;  3 HARDWARE RUIS-BYTES (SALT / IV) - VERANDER DIT PER BERICHT!
    ; ==========================================================
    LDI B 142           ; Ruis byte 1
    STO B 516           ; Openlijk op 516 voor de ontvanger
    LDI B 90            ; Ruis byte 2
    STO B 517           ; Openlijk op 517 voor de ontvanger
    LDI B 203           ; Ruis byte 3
    STO B 518           ; Openlijk op 518 voor de ontvanger

    LDI I 0             ; zet de index register
    ; LDI X 1             ; zet de stap grote
    
    LDI C 72            ; 'H'
    STX C 520
    INC I 
    LDI C 101           ; 'e'
    STX C 520
    INC I 
    LDI C 108           ; 'l'
    STX C 520
    INC I 
    LDI C 108           ; 'l'
    STX C 520
    INC I 
    LDI C 111           ; 'o'
    STX C 520
    INC I 
    LDI C 32            ; ' ' (Spatie) 32
    STX C 520
    INC I 
    LDI C 119           ; 'w'
    STX C 520
    INC I 
    LDI C 111           ; 'o'
    STX C 520
    INC I 
    LDI C 114           ; 'r'
    STX C 520
    INC I 
    LDI C 108           ; 'l'
    STX C 520
    INC I 
    LDI C 100           ; 'd'
    STX C 520
    INC I 
    
    LDI C 0             ; Null-terminator (Einde van het bericht)
    STX C 520

    

    ; ==========================================================
    ;  DE LUS: BEREKEN PIN-CODE SIGNATURE VANAF ADRES 520 TILL 0
    ; ==========================================================
        LDI I 0             ; Reset index register naar begin van de string (0)
        LDI A 0             ; Register A wordt onze PIN-code accumulator
        LDI Z 0             ; Register Z houden we op 0 voor de terminator-check

    PIN_LOOP:
        LDX C 520           ; Laad het karakter op (520 + I) in register C
        TSTE Z C            ; Is het geladen karakter gelijk aan 0 (Null-terminator)?
        JMPT PIN_DONE       ; JA? Dan zijn we klaar met de string! Spring uit de lus.

        ADD A C             ; NEE? Tel de ASCII-waarde van het karakter op bij A
        INC I               ; Verhoog de index I met stapgrootte X (1)
        JMP PIN_LOOP        ; Spring terug naar het begin van de lus

    PIN_DONE:
        STO A 513           ; Store de uiteindelijke PIN-code in 513

    ; --- HASH FUNCTIE: Hash(MasterKey, PIN) ---
        LDM M 512           ; M = Master Key
        LDM A 513           ; A = PIN-code Checksum
        
        XOR M A             ; Stap 1: Meng de PIN-code direct met de Master Key
        ROTL32 M 7          ; Stap 2: Roteer de hele boel 7 bits naar links
        SHIFTL A 3          ; Stap 3: Geef de PIN een extra shift-offset van 3 bits
        ADD M A             ; Stap 4: Smelt de twee gemanipuleerde waarden samen
        
        STO M 514           ; Sla de hash op in adres 514
        
    ; ==========================================================
    ;  ENCRYPTIE: EERST DE GENERATOR 3X KICKEN MET RUIS, DAN DE LUS
    ; ==========================================================
        LDM K 514           ; K = Basis-hash (de start-sleutel)

        LDM B 516           ; Grijp openbare ruis 1 (bijv. een random 32-bit getal)
        ADD K B             ; Meng de ruis direct in de status van K
        SM32_RND K 7        ; Kick 1: Roteer en mix met vaste constante 7

        LDM B 517           ; Grijp openbare ruis 2
        ADD K B             ; Meng ruis 2 in K
        SM32_RND K 7        ; Kick 2: Roteer en mix weer

        LDM B 518           ; Grijp openbare ruis 3
        ADD K B             ; Meng ruis 3 in K
        SM32_RND K 7        ; Kick 3: De ultieme synchronisatie-shake

        LDI I 0             ; Reset index I naar 0
        LDI Z 0             ; Nul-waarde voor terminator-check
        ; LDI X 1             ; Stapgrootte 1

    ENCRYPT_LOOP:
        LDX C 520           ; C = Geheugen[520 + I]
        
        TSTE Z C            ; Vergelijk C met 0
        JMPT ENCRYPT_DONE   ; Als nul, stop
        
        XOR C K             ; C = C XOR K (CPU stalt hier automatisch als K nog werkt!)
        STX C 532           ; Geheugen[532 + I] = C

        SM32_RND K 7        ; Binnen de lus rollen we supersnel door met vaste constante 7!
        
        INC I
        JMP ENCRYPT_LOOP    ; Terug naar start

    ENCRYPT_DONE:


    ; For debugging, change the pincode and/or mastercode here
    ; LDI Y 999
    ; STO Y 513       ; corrupt the pincode
    ; LDI Y 173
    ; STO Y 512       ; guess the mastercode
    
    ; --- RE-HASH FOR DECRYPTOR ---
        LDM M 512           
        LDM A 513           
        XOR M A             
        ROTL32 M 7          
        SHIFTL A 3          
        ADD M A             
        STO M 514           


    ; ==========================================================
    ;  DECRYPTIE: EXACT DEZELFDE 3 KICKS VÓÓR DE LUS START
    ; ==========================================================
        LDM K 514           ; Laad de Hash opnieuw in K

        LDM B 516           ; Grijp openbare ruis 1 (bijv. een random 32-bit getal)
        ADD K B             ; Meng de ruis direct in de status van K
        SM32_RND K 7        ; Kick 1: Roteer en mix met vaste constante 7

        LDM B 517           ; Grijp openbare ruis 2
        ADD K B             ; Meng ruis 2 in K
        SM32_RND K 7        ; Kick 2: Roteer en mix weer

        LDM B 518           ; Grijp openbare ruis 3
        ADD K B             ; Meng ruis 3 in K
        SM32_RND K 7        ; Kick 3: De ultieme synchronisatie-shake

        LDI I 0             ; Reset index I naar 0
        LDI Z 0             ; Nul-waarde voor terminator-check
        ; LDI X 1             ; Step-size

    DECRYPT_LOOP:
        LDX C 532           ; C = Versleutelde data uit [532+I]
        
        TSTE Z C            
        JMPT DECRYPT_DONE   
        
        XOR C K             ; (CPU stalt ook hier puur op de hardware-interlock van K)
        STX C 544           ; De gedecodeerde string komt op 544       

        SM32_RND K 7        ; Rol synchroon door met constante 7
                    
        INC I
        JMP DECRYPT_LOOP    

    DECRYPT_DONE:

        HALT
"""

# some assembly programming here to keep main.py clear and redeble
# assembly_program = """ 
#         ; --- XOR TEST PROGRAMMA ---
#             LDI K 487          ; value of the master key
#             LDI C 72           ; Laad data (72) in register C

#             XOR C K            ; D = D ^ M
#             STO C 520          ; Sla resultaat terug op in geheugen
#             HALT
#             """



assembly_program = """ 
    ;
; ==========================================================
;  TESTPROGRAMMA: SHIFTL EN ROTL32 HARDWARE VERIFICATIE
; ==========================================================
    ; --- DEEL 1: SHIFTL TEST (8-bits overflow check) ---
    LDI A 15            ; Laad getal 15 (binair: 0000 1111) in Register A
    SHIFTL A 4          ; Verschuif 4 posities links -> (binair: 1111 0000 = decimaal 240)
    STO A 520           ; Sla resultaat op op adres 100. Verwacht: 240

    LDI A 240           ; Laad getal 240 (binair: 1111 0000) opnieuw
    SHIFTL A 4          ; Verschuif nogmaals 4 posities links
                        ; In een pure 8-bits grens zou dit 0 worden, maar omdat
                        ; shftl_vw oneindig doorwerkt verwachten we hier:
                        ; binair: 1111 0000 0000 = decimaal 3840
    STO A 521           ; Sla op op adres 101. Verwacht: 3840

    ; --- DEEL 2: ROTL32 TEST (32-bits boundary wrap-around) ---
    LDI B 1             ; Laad getal 1 (binair: 31 nullen en een 1 helemaal rechts)
    ROTL32 B 1          ; Roteer 1 positie naar links
    STO B 522           ; Sla op op adres 102. Verwacht: 2

    ; Nu de ultieme test: we zetten een bit aan de linkerkant van het 32-bits venster
    ; Hexadecimaal 0x80000000 is decimaal 2147483648 (de allerhoogste bit staat aan)
    LDI B 2147483648    ; Hoogste bit (bit 31) is 1, de rest is 0
    ROTL32 B 1          ; Roteer 1 positie naar links. 
                        ; Die linker bit MOET er nu aan de rechterkant (bit 0) weer inrollen!
    STO B 523           ; Sla op op adres 103. Verwacht: 1 (de bit is rond gegaan!)

    ; --- DEEL 3: COMBINATIE TEST (Crypto-stijl mixing) ---
    LDI C 72            ; ASCII 'H' (binair: 0100 1000)
    ROTL32 C 8          ; Roteer 8 posities naar links -> schuift naar het tweede byte
    STO C 524           ; Sla op op adres 104. Verwacht: 18432

    HALT                ; Beëindig de simulatie en stop alle cores
        """



context_test = """
    ; ==========================================================
    ;  HOOFD-CPU CODE (Start vanaf PC = 0)
    ; ==========================================================
    LDI M 287454020     ; Adres 0: Laad de Master Key
    STO M 512           ; Adres 1: Sla op op 512
    LDI A 55            ; Adres 2: Bereid invoerwaarde voor de thread voor
    STO A 513           ; Adres 3: Sla PIN op op 513

    ; Start de parallelle thread! 
    ; Register A (waarde 55) wordt meegegeven als start-uCore.
    ; Het startadres van de thread-code begint exact op Adres 12.
    ; CONTEXT A 12        ; Adres 4: Lanceer THREAD_START op PC=12
    CONTEXT A THREAD_START

    ; Terwijl de thread asynchroon draait, doet de hoofd-CPU hier nuttig werk
    LDI B 10            ; Adres 5: R2 (B) = 10
    LDI X 10
    MUL B X             ; Adres 6: B = 10 * 10 = 100
    STO B 500           ; Adres 7: Sla 100 op op adres 500

    ; Jouw geïntegreerde JOIN-lus:
    ; We proberen te joinen. Als de thread NIET klaar is (fsm_state != 'DONE'),
    ; dan springt de hardware direct terug naar Adres 8 (zichzelf) en faalt de join.
    ; Als de thread WEL klaar is, oogst hij het resultaat in C en loopt de PC door naar 9.
WAIT_FOR_THREAD:
    ; JOIN A 9            ; Adres 8: Probeer te joinen in C. Indien niet klaar, spring naar 8.
    JOIN A WAIT_FOR_THREAD

    STO A 514           ; Adres 9: Succes! Sla het geoogste thread-resultaat op op 501
    HALT                ; Adres 10: Hoofd-CPU stopt.

    ; ==========================================================
    ;  THREAD CONTEXT CODE (Begint exact op PC = 11)
    ; ==========================================================
THREAD_START:
    LDI B 5             ; Adres 11: R2 (B) = 5
    MUL A B             ; Adres 12: R1 (A) = A + B = 55 + 5 = 60
    CLOSE               ; Adres 13: Thread is klaar, uCore in A blijft VALID!
"""

context_test1 = """
; ==========================================================
;  HOOFD-CPU: MULTI-CONTEXT STRESS TEST
; ==========================================================
    ; Stap 1: Bereid de invoerwaarden voor in registers
    LDI A 10            ; Thread 1 invoer = 10
    LDI B 20            ; Thread 2 invoer = 20
    LDI C 30            ; Thread 3 invoer = 30

    ; Stap 2: Lanceer 3 contexten parallel!
    ; De assembler lost de labels THREAD_1, THREAD_2, THREAD_3 direct op.
    CONTEXT A THREAD_1  ; Lanceer Thread 1 (werkt met uCore van A)
    CONTEXT B THREAD_2  ; Lanceer Thread 2 (werkt met uCore van B)
    CONTEXT C THREAD_3  ; Lanceer Thread 3 (werkt met uCore van C)

    ; Terwijl er nu 3 uCores tegelijk vechten om de round-robin ticks,
    ; doet de hoofd-CPU zelf ook nog een flinke achtergrondklus:
    LDI X 5
    LDI Y 5
    MUL X Y             ; X = 5 * 5 = 25
    STO X 500           ; Sla resultaat van hoofd-CPU op op adres 500

    

    ; ==========================================================
    ;  HARDWARE SYNCHRONISATIE BARRIÈRE (The OCCAM Join)
    ; ==========================================================
WAIT_T1:
    JOIN A WAIT_T1      ; Wacht op Thread 1. Indien klaar: oogst resultaat in A.
    STO A 512           ; Sla resultaat Thread 1 op op adres 512

WAIT_T2:
    JOIN B WAIT_T2      ; Wacht op Thread 2. Indien klaar: oogst resultaat in B.
    STO B 513           ; Sla resultaat Thread 2 op op adres 513

WAIT_T3:
    JOIN C WAIT_T3      ; Wacht op Thread 3. Indien klaar: oogst resultaat in C.
    STO C 514           ; Sla resultaat Thread 3 op op adres 514

    LDI Z 0
    LD Z C

    HALT                ; Volledige systeemstop!

; ==========================================================
;  PARALLELLE THREAD CODES (Draaien asynchroon)
; ==========================================================
THREAD_1:
    LDI X 5
    MUL A X             ; A = 10 * 5 = 50 (Zware uCore MUL!)
    CLOSE               ; Beëindig thread, uCore in A blijft VALID

THREAD_2:
    LDI X 10
    MUL B X             ; B = 20 * 10 = 200 (Zware uCore MUL!)
    CLOSE               ; Beëindig thread, uCore in B blijft VALID

THREAD_3:
    LDI X 100
    ADD C X             ; C = 30 + 100 = 130 (Snelle uCore ADD)
    CLOSE               ; Beëindig thread, uCore in C blijft VALID
"""


context_test1a = """
; ==========================================================
;  HOOFD-CPU: MULTI-CONTEXT STRESS TEST
; ==========================================================
    ; Stap 1: Bereid de invoerwaarden voor in registers
    LDI A 10            ; Thread 1 invoer = 10
    LDI B 20            ; Thread 2 invoer = 20
    LDI C 30            ; Thread 3 invoer = 30

    ; Terwijl er nu 3 uCores tegelijk vechten om de round-robin ticks,
    ; doet de hoofd-CPU zelf ook nog een flinke achtergrondklus:
    LDI X 5
    LDI Y 5
    MUL X Y             ; X = 5 * 5 = 25
    
    ; ==========================================================
    ;  HARDWARE SYNCHRONISATIE BARRIÈRE (The OCCAM Join)
    ; ==========================================================

    LDI X 5
    MUL A X             ; A = 10 * 5 = 50 (Zware uCore MUL!)
    

    LDI X 10
    MUL B X             ; B = 20 * 10 = 200 (Zware uCore MUL!)
    
WAIT_T3:
    LDI X 100
    ADD C X             ; C = 30 + 100 = 130 (Snelle uCore ADD)

    STO X 500           ; Sla resultaat van hoofd-CPU op op adres 500
    STO A 512           ; Sla resultaat Thread 1 op op adres 512
    STO B 513           ; Sla resultaat Thread 2 op op adres 513
    STO C 514           ; Sla resultaat Thread 3 op op adres 514
    

    HALT                ; Volledige systeemstop!

;
"""


context_stress = """
; ==========================================================
;  15x CONTEXT STRESSTEST (Gecorrigeerd)
; ==========================================================
    LDI A 5             ; Bronwaarde voor de threads (blijft ALTIJD 1)
    LDI I 0             ; Lus-teller I = 0
    LDI Y 150            ; De doelwaarde (15 iteraties)
    LDI X 0             ; Totaalteller X = 0
    
SPAWN_LOOP:
    TSTE I Y            
    JMPT FLUSH_REMAINING 

    CONTEXT A THREAD_WORKER 
    FAIL MATRIX_FULL_HANDLER  

    INC I   

    JOIN B SPAWN_LOOP
    ADD X B

    JMP SPAWN_LOOP      

MATRIX_FULL_HANDLER:
    ; Oogst in register B in plaats van A! Hierdoor blijft Master-register A intact.
    JOIN B MATRIX_FULL_HANDLER 
    
    ADD X B             ; Tel het resultaat uit B op bij het totaal X

    JMP SPAWN_LOOP

; ==========================================================
;  FINALE FLUSH
; ==========================================================
FLUSH_REMAINING:
    ; Oogst ook hier in register B!
    JOIN B ALL_DONE     

    ADD X B
    JMP FLUSH_REMAINING

ALL_DONE:

    SYNC FLUSH_REMAINING

    STO X 512           ; Sla het eindresultaat op op adres 512
    HALT                

; ==========================================================
;  PARALLELLE WORKER THREAD CODE
; ==========================================================
THREAD_WORKER: 
    LDI M 42
    LDI L 42
    MUL M L

    LDI B 1             
    MUL B A  

    RETURN B
    ;CLOSE
"""


display_test = """
; ==============================================================================
;  STERN-Z32 PLATFORM: FULL PERIPHERAL INTEGRATION TEST
;  Doel: KBD input uitlezen, echoën naar TextDisplay en plotten op GraphDisplay
; ==============================================================================

    LDI Z 0             ; Register Z = 0 (Gebruikt voor de NULL-check van KBD)
    LDI Y 1             ; Register Y = 1 (Constante voor Device Type 1: Karakter)
    LDI X 2             ; Register X = 2 (Constante voor Device Type 2: Grafisch)
    LDI L 27

    CONTEXT Z REFRESH

    ; We zetten alvast een vaste startpositie klaar voor het grafische display
    LDI B 100           ; B = X-as coördinaat (start op 100)
    LDI C 100           ; C = Y-as coördinaat (start op 100)

IO_POLL_LOOP:
    ; IOSYNC              ; Geef de IO-controller een kloktik om buffers te verversen
    
    ; --- STAP 1: LEES KEYBOARD ---
    IN A 6              ; Lees invoerreg6 (KBD) uit naar Register A
    TSTE A Z            ; Vergelijk de ingelezen waarde met 0 (NULL)
    JMPT IO_POLL_LOOP   ; Als A == 0 (geen toets ingedrukt), vlieg direct terug in de lus

    TSTE A L
    JMPT END

    ; --- STAP 2: ECHO NAAR CHARACTER DISPLAY ---
    OUT Y 0             ; Schrijf Devicetype 1 (Karakter) naar reg0
    OUT A 1             ; Schrijf de ASCII-waarde van de toets naar reg1 (value1)
    LDI K 1             ; Instructie 1 = Print karakter
    OUT K 5             ; Schrijf naar reg5 -> activeert de write_flag!

    ; IOSYNC

    ; --- STAP 3: PLOT SYNCHROON OP GRAPHICAL DISPLAY ---
    OUT X 0             ; Schrijf Devicetype 2 (Grafisch) naar reg0
    LDI K 2             ; Kleurcode 2 (Rood) naar Register K
    OUT K 1             ; Schrijf kleur naar reg1 (value1)
    OUT B 2             ; Schrijf huidige X-coördinaat (B) naar reg2 (value2)
    OUT C 3             ; Schrijf huidige Y-coördinaat (C) naar reg3 (value3)
    LDI K 2             ; Instructie 2 = Plot pixel
    OUT K 5             ; Schrijf naar reg5 -> activeert de write_flag!

    ; --- STAP 4: UPDATE PARAMETERS VOOR HET VOLGENDE KARAKTER ---
    INC B               ; Verschuif de X-as voor de volgende plot (schuin lijntje)
    INC C               ; Verschuif de Y-as
    
    JMP IO_POLL_LOOP    ; Spring terug en wacht op de volgende toetsaanslag

END:
    HALT

REFRESH:
    IOSYNC
    JMP REFRESH
"""








context_test2 = """
; ==============================================================================
;  PARALLEL MATRIX ENCRYPTIE & DECRYPTIE PROGRAMMA (INMOS-Z32 EDITION)
;  Strategie: Master-CPU geeft karakter (C) mee via CONTEXT en regelt de opslag.
; ==============================================================================

    LDI M 287454020     ; Master Key
    STO M 512           ; Sla op op adres 512

    ; Hardware ruis-bytes (Salt / IV)
    LDI B 142           
    STO B 516           ; Openlijk op 516 voor de ontvanger
    LDI B 90            
    STO B 517           ; Openlijk op 517 voor de ontvanger
    LDI B 203           
    STO B 518           ; Openlijk op 518 voor de ontvanger

    ; --- DATA INITIALISATIE (Origineel bericht vanaf adres 520) ---
    LDI I 0             
    LDI C 72            ; 'H'
    STX C 520
    INC I 
    LDI C 101           ; 'e'
    STX C 520
    INC I 
    LDI C 108           ; 'l'
    STX C 520
    INC I 
    LDI C 108           ; 'l'
    STX C 520
    INC I 
    LDI C 111           ; 'o'
    STX C 520
    INC I 
    LDI C 32            ; ' ' (Spatie)
    STX C 520
    INC I 
    LDI C 119           ; 'w'
    STX C 520
    INC I 
    LDI C 111           ; 'o'
    STX C 520
    INC I 
    LDI C 114           ; 'r'
    STX C 520
    INC I 
    LDI C 108           ; 'l'
    STX C 520
    INC I 
    LDI C 100           ; 'd'
    STX C 520
    INC I 
    LDI C 0             ; Null-terminator (Einde van het bericht)
    STX C 520

    ; ==========================================================
    ;  FASE 1: BEREKEN PIN-CODE SIGNATURE & PRE-SHARES SLEUTEL (SERIEEL)
    ; ==========================================================
    LDI I 0             ; Reset index register naar begin van de string (0)
    LDI A 0             ; Register A wordt onze PIN-code accumulator
    LDI Z 0             ; Register Z houden we op 0 voor de terminator-check

PIN_LOOP:
    LDX C 520           ; Laad het karakter op (520 + I) in register C
    TSTE Z C            ; Is het geladen karakter gelijk aan 0 (Null-terminator)?
    JMPT PIN_DONE       ; JA? Spring uit de lus.

    ADD A C             ; NEE? Tel de ASCII-waarde op bij A
    INC I               ; Verhoog de index I
    JMP PIN_LOOP        

PIN_DONE:
    STO A 513           ; Store de uiteindelijke PIN-code in 513

    ; --- HASH FUNCTIE: Hash(MasterKey, PIN) ---
    LDM M 512           ; M = Master Key
    LDM A 513           ; A = PIN-code Checksum
    
    XOR M A             ; Meng de PIN-code met de Master Key
    ROTL32 M 7          ; Roteer 7 bits naar links
    SHIFTL A 3          ; Geef de PIN een extra shift-offset van 3 bits
    ADD M A             ; Smelt de twee waarden samen
    STO M 514           ; Sla de basis-hash op in adres 514
    
    ; --- DE 3 OPENBARE RUIS-KICKS ---
    LDM K 514           ; K = Basis-hash

    LDM B 516           ; Grijp openbare ruis 1
    ADD K B             ; Meng de ruis in K
    SM32_RND K 7        ; Kick 1

    LDM B 517           ; Grijp openbare ruis 2
    ADD K B             
    SM32_RND K 7        ; Kick 2

    LDM B 518           ; Grijp openbare ruis 3
    ADD K B             
    SM32_RND K 7        ; Kick 3: Volledig gesynchroniseerd!

    STO K 515           ; Sla deze stabiele basis-keystream op op adres 515 voor de workers


    ; ==========================================================
    ;  FASE 2: ENCRYPTIE LUS (MASTER STUURT DATA, WORKER REKENT)
    ; ==========================================================
    LDI I 0             ; Reset index I naar 0
    LDI Z 0             ; Nul-waarde voor terminator-check

ENCRYPT_LOOP:
    LDX C 520           ; C = Geheugen[520 + I]
    
    TSTE Z C            ; Vergelijk C met 0
    JMPT ENCRYPT_DONE   ; Als nul, stop de encryptie-lus
    
    ; Lanceer de thread. De uCore krijgt de waarde van Register C mee!
    CONTEXT C THREAD_ENCRYPT_WORKER 

    ; De Master-CPU wacht hier op de hardware-interlock tot deze specifieke uCore klaar is.
    ; Zodra de worker 'CLOSE' aanroept, landt de versleutelde byte weer in ons Register C.
WAIT_FOR_ENC_CORE:
    JOIN C WAIT_FOR_ENC_CORE 

    ; Sla het geoogste resultaat op de juiste indexpositie op
    STX C 532           ; Geheugen[532 + I] = Versleutelde byte
    
    INC I               ; Volgende karakter
    JMP ENCRYPT_LOOP    

ENCRYPT_DONE:



    ; ==========================================================
    ;  FASE 3: DECRYPTIE LUS (EXACT DEZELFDE PARALLELLE LOGICA)
    ; ==========================================================
    LDI I 0             ; Reset index I naar 0

DECRYPT_LOOP:
    LDX C 532           ; C = Versleutelde data uit Geheugen[532 + I]
    
    TSTE Z C            ; Vergelijk C met 0 (einde encrypted string)
    JMPT DECRYPT_DONE   ; Als nul, stop de decryptie-lus
    
    ; Lanceer de decryptie worker en geef de encrypted byte mee via C
    CONTEXT C THREAD_DECRYPT_WORKER 

    ; Wacht tot de uCore de SM32_RND en XOR heeft afgerond
WAIT_FOR_DEC_CORE:
    JOIN C WAIT_FOR_DEC_CORE 

    ; Schrijf de herstelde byte weg via de gecontroleerde Master-index
    STX C 544           ; De gedecodeerde string komt op Geheugen[544 + I]       
                
    INC I               
    JMP DECRYPT_LOOP    

DECRYPT_DONE:
    HALT                ; Het programma is succesvol doorlopen!


; ==============================================================================
;  HARDWARE WORKER THREAD CODE BLOKKEN (Draaien autonoom op de uCores matrix)
; ==============================================================================

THREAD_ENCRYPT_WORKER:
    ; Bij de start bevat ons lokale Register A (R1) de waarde van de byte
    ; die de Master CPU via de CONTEXT-instructie heeft meegegeven.

    LDM K 515           ; Haal de pre-shared basis-sleutel op uit het geheugen
    SM32_RND K 7        ; Voer de zware cryptografische transformatie uit

    XOR C K             ; Versleutel de byte: A = A XOR K

    ; We geven de waarde in Register A terug aan de Master via de CLOSE/JOIN hardware.
    CLOSE               ; Lever de uCore terug aan de matrix-pool!


THREAD_DECRYPT_WORKER:
    ; Identiek aan de encryptie-worker, maar herstelt de data
    LDM K 515           
    SM32_RND K 7        

    XOR C K             ; XOR met dezelfde K heft de encryptie weer op

    CLOSE               ; Geef de core vrij en retourneer de waarde in A
"""