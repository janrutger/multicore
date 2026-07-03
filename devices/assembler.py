# assembler.py
from opcodes import Op

# Handige mapping voor de registernummers
REGISTERS = {
    'I': 0, 'R0': 0,
    'A': 1, 'R1': 1,
    'B': 2, 'R2': 2,
    'C': 3, 'R3': 3,
    'K': 4, 'R4': 4,
    'L': 5, 'R5': 5,
    'M': 6, 'R6': 6,
    'X': 7, 'R7': 7,
    'Y': 8, 'R8': 8,
    'Z': 9, 'R9': 9,
}

def assemble(source_code: str) -> list:
    """Vertaalt STERN assembly tekst naar een lijst met machinecode integers."""
    lines = []
    
    # --- STAP 1: Schoonmaken van de code ---
    for line in source_code.splitlines():
        # Verwijder comments en spaties aan de randen
        line = line.split(';')[0].strip()
        if not line:
            continue
        lines.append(line)

    # --- STAP 2: PASS 1 - Labels verzamelen ---
    labels = {}
    instruction_lines = []
    current_address = 0

    for line in lines:
        if line.endswith(':'):
            # Dit is een label (bijv. "ELSE_TAK:")
            label_name = line[:-1].strip()
            labels[label_name] = current_address
        else:
            # Dit is een daadwerkelijke instructie
            instruction_lines.append(line)
            current_address += 1

    # --- STAP 3: PASS 2 - Vertalen naar STERN Machinecode ---
    machine_code = []

    for current_address, line in enumerate(instruction_lines):
        parts = line.replace(',', ' ').split()
        mnemonic = parts[0].upper()
        
        # Haal de opcode op uit je Op IntEnum
        if not hasattr(Op, mnemonic):
            raise SyntaxError(f"Onbekende instructie '{mnemonic}' op adres {current_address}")
        opcode = int(getattr(Op, mnemonic))

        # FORMAT: ZERO (Geen argumenten, bijv. HALT, NOP)
        if len(parts) == 1:
            machine_code.append(opcode)
            continue

        # FORMAT: ONE_ADDR (Sprongen naar labels of harde adressen, bijv. JMP, JMPF)
        if mnemonic in ['JMP', 'JMPF', 'JMPT', 'CALL']:
            target = parts[1]
            # Check of het argument een bekend label is, anders aannemen dat het een getal is
            addr = labels[target] if target in labels else int(target)
            val = addr * 100 + opcode
            machine_code.append(val)
            continue

        # === FORMAT: ONE_REG (Bijv: INC K of DEC A) ===
        if mnemonic in ['INC', 'DEC']:
            reg1_str = parts[1].upper()
            if reg1_str not in REGISTERS:
                raise SyntaxError(f"Onbekend register '{reg1_str}' op adres {current_address}")
            reg1 = REGISTERS[reg1_str]
            
            # Formaatopbouw voor ONE_REG: we stoppen het registernummer op de plek van reg1.
            # Afhankelijk van hoe je decoder in cpu.py dit verwacht (bijv. (reg1 * 100) + opcode 
            # of (reg1 * 10) + opcode. Gezien je andere formaten is reg1 meestal de eenheid/tiental voor de opcode):
            val = reg1 * 100 + opcode  # Verander dit naar jouw specifieke bit/integer layout shift!
            machine_code.append(val)
            continue

        # FORMAT: TWO_REG_VAL / TWO_REG_ADDR / TWO_REG_REG
        # (Bijv: LDI A 42 of TSTE A B of STO A 100)
        reg1_str = parts[1].upper()
        if reg1_str not in REGISTERS:
            raise SyntaxError(f"Onbekend register '{reg1_str}' op adres {current_address}")
        reg1 = REGISTERS[reg1_str]

        arg2_str = parts[2].upper()
        
        # Is het tweede argument een register? (Bijv. TSTE A B of ADD A B)
        if arg2_str in REGISTERS:
            reg2 = REGISTERS[arg2_str]
            val = (reg2 * 10 + reg1) * 100 + opcode
        else:
            # Het is een directe waarde of een geheugenadres (Bijv. LDI A 42 of STO A 100)
            # Check ook of het tweede argument stiekem een label is (handig voor variabelen in het RAM!)
            arg2 = labels[arg2_str] if arg2_str in labels else int(arg2_str)
            val = (arg2 * 10 + reg1) * 100 + opcode

        machine_code.append(val)

    return machine_code