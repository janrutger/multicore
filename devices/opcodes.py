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