# opcodes.py
from enum import IntEnum

class Op(IntEnum):
    # --- FORMAT: ZERO ---
    NOP   = 10
    HALT  = 11
    RET   = 12
    EI    = 13
    DI    = 14
    RTI   = 15

    # --- FORMAT: ONE_ADDR ---
    JMPF  = 20
    JMPT  = 21
    JMP   = 22
    CALL  = 24
    CALLX = 25
    INT   = 26

    # --- FORMAT: TWO_REG_VAL / TWO_REG_ADDR ---
    LD    = 30  
    LDI   = 31
    LDM   = 32
    LDX   = 33
    STO   = 40
    STX   = 41
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
    ADD   = 50  
    SUB   = 52
    MUL   = 60
    DMOD  = 65
    TSTE  = 71
    TSTG  = 72

    # --- FORMAT: ONE_REG ---
    PUSH  = 90
    POP   = 91
    GPU   = 94
    CALLS = 95

# Vaste sets voor de decoder om snel het format te matchen
FORMAT_ZERO        = {Op.HALT, Op.RET, Op.EI, Op.DI, Op.RTI}
FORMAT_ONE_ADDR    = {Op.JMPF, Op.JMPT, Op.JMP, Op.CALL, Op.CALLX, Op.INT}
FORMAT_ONE_REG     = {Op.PUSH, Op.POP, Op.GPU, Op.CALLS}
FORMAT_TWO_REG_REG = {Op.LD, Op.ADD, Op.SUB, Op.MUL, Op.DMOD, Op.TSTE, Op.TSTG}

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





# ucode instructions

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
    ]
}