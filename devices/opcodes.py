# opcodes.py
from enum import IntEnum

class Op(IntEnum):
    # --- FORMAT: ZERO ---
    NOP   = 10
    HALT  = 11      # Implemented
    RET   = 12
    EI    = 13
    DI    = 14
    RTI   = 15

    # --- FORMAT: ONE_ADDR ---
    JMPF  = 20      # Implemented
    JMPT  = 21      # Implemented
    JMP   = 22      # Implemented
    CALL  = 24
    CALLX = 25
    INT   = 26

    # --- FORMAT: TWO_REG_VAL / TWO_REG_ADDR --- 
    LDI   = 31      # Implemented
    LDM   = 32      # Implemented
    LDX   = 33      # Implemented
    STO   = 40      # Implemented
    STX   = 41      # Implemented
    ADDI  = 51
    SUBI  = 53
    MULI  = 61
    DIVI  = 63
    TST   = 70
    INC   = 80
    DEC   = 81
    ANDI  = 82
    STACK = 92
    USTACK= 93

    # --- FORMAT: TWO_REG_REG ---
    LD    = 30 
    ADD   = 50      # Implemented 
    SUB   = 52
    MUL   = 60      # Implemented
    MOD   = 65      # Implemented
    TSTE  = 71      # Implemented
    TSTG  = 72
    XOR   = 42      # Implemented

    # --- FORMAT: ONE_REG ---
    PUSH  = 90
    POP   = 91
    GPU   = 94
    CALLS = 95

# Vaste sets voor de decoder om snel het format te matchen
FORMAT_ZERO        = {Op.HALT, Op.RET, Op.EI, Op.DI, Op.RTI}
FORMAT_ONE_ADDR    = {Op.JMPF, Op.JMPT, Op.JMP, Op.CALL, Op.CALLX, Op.INT}
FORMAT_ONE_REG     = {Op.PUSH, Op.POP, Op.GPU, Op.CALLS}
FORMAT_TWO_REG_REG = {Op.LD, Op.ADD, Op.SUB, Op.MUL, Op.MOD, Op.TSTE, Op.TSTG, Op.XOR}
FORMAT_TWO_REG_VAL = {Op.LDI, Op.LDM, Op.LDX, Op.STO, Op.STX, Op.ADDI, Op.SUBI, Op.MULI, Op.DIVI, Op.TST, Op.ANDI}

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
    'stv':    ['mv_vt',  'setResult'],
    'status': ['status', 'setResult'],

    'add':    ['valid_v', 'valid_w', 'add', 'setResult'],
    'sub':    ['valid_v', 'valid_w', 'sub', 'setResult'],
    'mul':    ['valid_v', 'valid_w', 'mul', 'setResult'],
    'div':    ['valid_v', 'valid_w', 'div', 'setResult'],

    'tstz':   ['valid_v', 'tstz', 'setResult'],
    'tstn':   ['valid_v', 'tstn', 'setResult'],

    'cmpe':   ['valid_v', 'valid_w', 'cmpe',  'setResult'],
    'cmpne':  ['valid_v', 'valid_w', 'cmpne', 'setResult'],
    'cmpgt':  ['valid_v', 'valid_w', 'cmpgt', 'setResult'],
    'cmplt':  ['valid_v', 'valid_w', 'cmplt', 'setResult'],

    'xor_vw': ['valid_v', 'valid_w', 'xor_vw','setResult'],

   'slow_mul': [
        'valid_v',             # 0: Wacht op A en onthoud teken
        'valid_w',             # 1: Wacht op B en onthoud teken
        'abs_v',               # 2: Maak V positief voor de lus
        'abs_w',               # 3: Maak W positief voor de lus
        
        # --- SWAP OPTIMALISATIE ---
        'cmplt',               # 4: Is V < W?
        ('bra_true', 4),       # 5: JA? Sla de swap over! Spring +4 verder -> naar clr_t (index 9)
        'mv_vt',               # 6: T = V
        'mv_vw',               # 7: V = W (V is nu de kleinste teller!)
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
        'mv_vw',           # 3: V = W (Zet de deler W tijdelijk in V om te kunnen testen)
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
    ]
}





# some assembly programming here to keep main.py clear and redeble
# assembly_program = """ 
#         ; --- XOR TEST PROGRAMMA ---
#             LDI K 487          ; value of the master key
#             LDI C 72           ; Laad data (72) in register C

#             XOR C K            ; D = D ^ M
#             STO C 520          ; Sla resultaat terug op in geheugen
#             HALT
#             """


# lets write the encrypt and decrypt method
# total 1024 main memory 
encrypt_program = """
    LDI M 251           ; Value of the master key
    STO M 512           ; Store masterkey at 512

    LDI I 0             ; zet de index register
    LDI X 1             ; zet de stap grote
    
    LDI C 72            ; 'H'
    STX C 520
    ADD I X
    LDI C 101           ; 'e'
    STX C 520
    ADD I X
    LDI C 108           ; 'l'
    STX C 520
    ADD I X
    LDI C 108           ; 'l'
    STX C 520
    ADD I X
    LDI C 111           ; 'o'
    STX C 520
    ADD I X
    LDI C 32            ; ' ' (Spatie) 32
    STX C 520
    ADD I X
    LDI C 119           ; 'w'
    STX C 520
    ADD I X
    LDI C 111           ; 'o'
    STX C 520
    ADD I X
    LDI C 114           ; 'r'
    STX C 520
    ADD I X
    LDI C 108           ; 'l'
    STX C 520
    ADD I X
    LDI C 100           ; 'd'
    STX C 520
    ADD I X
    
    LDI C 0             ; Null-terminator (Einde van het bericht)
    STX C 520
    ADD I X
    



    ; create the PIN-code signature by adding the char values of the message
    ; Store de PIN-code in 513
    ; ==========================================================
    ;  DE LUS: BEREKEN PIN-CODE SIGNATURE VANAF ADRES 520 TILL 0
    ; ==========================================================
        LDI I 0             ; Reset index register naar begin van de string (0)
        LDI A 0             ; Register A wordt onze PIN-code accumulator
        LDI Z 0             ; Register Z houden we op 0 voor de terminator-check

    PIN_LOOP:
        LDX C 520           ; Laad het karakter op (520 + I) in register C
        TSTE C Z            ; Is het geladen karakter gelijk aan 0 (Null-terminator)?
        JMPT PIN_DONE       ; JA? Dan zijn we klaar met de string! Spring uit de lus.

        ADD A C             ; NEE? Tel de ASCII-waarde van het karakter op bij A
        ADD I X             ; Verhoog de index I met stapgrootte X (1)
        JMP PIN_LOOP        ; Spring terug naar het begin van de lus

    PIN_DONE:
        STO A 513           ; Store de uiteindelijke PIN-code in 513

    ; --- HASH FUNCTIE: Hash(MasterKey, PIN) ---
    ; Gebruik Register M (512) en A (513)
        LDM M 512           ; M = Master Key
        LDM A 513           ; A = PIN-code Checksum

        ; --- EENVOUDIGE MIX-OPERATIE ---
        ; We willen: Hash = (M XOR A) + (M ROL 3) of iets dergelijks
        ; Omdat we geen ROL (Rotate Left) hebben, gebruiken we vermenigvuldiging
        
        LDI B 31            ; Een priemgetal als "mixer" voor spreiding
        MUL M B             ; M = M * 31 (Dit zorgt voor een bit-shift effect)
        
        ; Nu de PIN erbij mengen
        ADD M A             ; Voeg de PIN toe aan de gemixte Master Key
        
        ; Store de uiteindelijke Hash
        STO M 514           ; Sla de hash op in adres 514
        
    ; ==========================================================
    ;  GEOPTIMALISEERDE ENCRYPTIE LUS: DATA (520+I) XOR HASH -> (532+I)
    ; ==========================================================
        LDM K 514           ; K = Hash (de encryptie-sleutel)
        LDI I 0             ; Reset index I naar 0
        LDI Z 0             ; Nul-waarde voor terminator-check
        LDI X 1             ; Stapgrootte 1

    ENCRYPT_LOOP:
        LDX C 520           ; C = Geheugen[520 + I]
        
        ; Test op de null-terminator
        TSTE C Z            ; Vergelijk C met 0
        JMPT ENCRYPT_DONE   ; Als nul, stop
        
        ; De XOR operatie
        XOR C K             ; C = C XOR K
        
        ; Opslaan op de nieuwe locatie (offset 532)
        STX C 532           ; Geheugen[532 + I] = C
        
        ; Ophogen van index
        ADD I X             ; I = I + 1
        
        JMP ENCRYPT_LOOP    ; Terug naar start

    ENCRYPT_DONE:

    ; For debugging, change the pincode here
    ; LDI Y 999
    ; STO Y 513




    ; --- HASH FUNCTIE: Hash(MasterKey, PIN) ---
    ; Gebruik Register M (512) en A (513)
        LDM M 512           ; M = Master Key
        LDM A 513           ; A = PIN-code Checksum

        ; --- EENVOUDIGE MIX-OPERATIE ---
        ; We willen: Hash = (M XOR A) + (M ROL 3) of iets dergelijks
        ; Omdat we geen ROL (Rotate Left) hebben, gebruiken we vermenigvuldiging
        
        LDI B 31            ; Een priemgetal als "mixer" voor spreiding
        MUL M B             ; M = M * 31 (Dit zorgt voor een bit-shift effect)
        
        ; Nu de PIN erbij mengen
        ADD M A             ; Voeg de PIN toe aan de gemixte Master Key
        
        ; Store de uiteindelijke Hash
        STO M 514           ; Sla de hash op in adres 514


    ; ==========================================================
    ;  DECRYPTIE LUS: DATA (532+I) XOR HASH -> (540+I)
    ; ==========================================================
        LDM K 514           ; Laad de Hash (de sleutel) opnieuw in K
        LDI I 0             ; Reset index I naar 0
        LDI Z 0             ; Nul-waarde voor terminator-check
        LDI X 1             ; Step-size

    DECRYPT_LOOP:
        LDX C 532           ; C = Versleutelde data uit [532+I]
        
        ; Test op de null-terminator (we verwachten dat die er nog steeds staat)
        TSTE C Z            
        JMPT DECRYPT_DONE   
        
        ; De XOR operatie (draait de encryptie exact terug)
        XOR C K             
        
        ; Opslaan op de nieuwe locatie (de gedecodeerde string komt op 544)
        STX C 544            
                    
        ADD I X             ; I++
        
        JMP DECRYPT_LOOP    

    DECRYPT_DONE:


        HALT
"""




#### Other assembly test programs
# Je volledige programma, nu super leesbaar met labels!
    # assembly_program = """
    # LDI  A, 0        ; Laad accumulator A met 42
    # LDI  B, 100      ; Laad register B met 42
    # LDI  C, 1
    # TEST:
    #     TSTE A, B          ; Vergelijk Register A en Register B
    #     JMPT END_IF      ; Spring naar de ELSE-tak als uitkomst False is
    
    #     ADD A, C     ; ELSE-tak: Zet A op 11
    #     JMP TEST
        
    # END_IF:
    #     LDI A, 99
    #     STO  A, 100    ; Sla de uiteindelijke waarde van A op op RAM-adres 100
    #     HALT           ; Einde van de simulatie
    # """
    # assembly_program = """ 
    #     LDI A -42         ; Activeert een core om A = 4 te maken
    #     LDI B 4200        ; Activeert een core om B = 3 te maken
    #     MUL A B         ; CPU delegeert 'slow_mul' aan een nieuwe core met arg1=Core_A en arg2=Core_B
    #     STO A 100       ; CPU stalled tot de MUL core VALID is, en schrijft 12 naar adres 50
    #     HALT 
    # """
    # assembly_program = """ 
    #     ; --- INITIALISATIE ---
    #     LDI A 0            ; Register A = Onze loop-counter (start op 0)
    #     LDI B 100            ; Register B = De doelwaarde van de counter (3)
    #     LDI C 1            ; Register C = De stapgrootte (+1 per ronde)
    #     LDI X 0            ; Register X = De totale som-accumulator (start op 0)
    #     LDI Y 5            ; Register Y = De vaste waarde die we telkens vermenigvuldigen (5)

    # LOOP:
    #     ; --- TEST LUSCONDITIE ---
    #     TSTE A B           ; Vergelijk counter (A) met doelwaarde 3 (B)
    #     JMPT END_LOOP      ; Als A == 3 (True), spring uit de lus naar END_LOOP

    #     ; --- BEREKENING ---
    #     MUL Y A            ; Activeer core voor Y * A (de huidige stap)
    #     ADD X Y            ; CPU stalled tot de MUL core VALID is, en telt op bij X

    #     ; --- TELLER OPHOGEN ---
    #     ADD A C            ; A = A + 1 (Verhoog counter)

    #     ; --- REFRESH INVOER ---
    #     LDI Y 5            ; Overschrijf register Y met de schone waarde 5
    #                        ; om te voorkomen dat het oude Core-ID als invoer dient

    #     JMP LOOP           ; Spring onvoorwaardelijk terug naar de start van de lus

    # END_LOOP:
    #     ; --- AFRASTING EN OPSLAG ---
    #     STO X 100          ; Sla de totale som (X) op op RAM-adres 100
    #     HALT               ; Sluit de simulatie af
    # """

    # assembly_program = """ 
    #     LDI A 18
    #     LDI B 5
    #     MOD A B
    #     HALT
    # """

assembly_program = """ 
    ;
        LDI A 1
        LDI B 2
        LDI C -3
        LDI K 4
        LDI L 5
        LDI M 6
        LDI Y 7
        LDI X 8
        LDI Z 9

        MUL A B
        MUL A B
        MUL A B
        MUL A B
        MUL A B

        MUL A B
        MUL A B
        MUL A B
        MUL A B
        MUL A B
        
        MUL A B
        MUL A B
        MUL A B
        MUL A B
        MUL A B

        MUL A B
        MUL A B
        MUL A B
        MUL A B
        MUL A B
        

        
        HALT
        """