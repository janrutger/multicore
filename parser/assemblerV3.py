# assembler.py
# assembler.py
import sys
import os

# Voeg de specifieke map direct toe aan het zoekpad
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../SternZ32G")))

from opcodes import (
    Op, 
    FORMAT_ZERO, 
    FORMAT_ONE_ADDR, 
    FORMAT_ONE_REG, 
    FORMAT_TWO_REG_REG, 
    FORMAT_TWO_REG_VAL
)

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
            # FIX: Altijd naar UPPERCASE om case-sensitivity fouten te voorkomen!
            label_name = line[:-1].strip().upper()
            labels[label_name] = current_address
        else:
            # Dit is een daadwerkelijke instructie
            instruction_lines.append(line)
            current_address += 1

    # # --- STAP 3: PASS 2 - Vertalen naar STERN Machinecode ---
    # machine_code = []

    # for current_address, line in enumerate(instruction_lines):
    #     parts = line.replace(',', ' ').split()
    #     mnemonic = parts[0].upper()
        
    #     # Haal de opcode op uit je Op IntEnum
    #     if not hasattr(Op, mnemonic):
    #         raise SyntaxError(f"Onbekende instructie '{mnemonic}' op adres {current_address}")
        
    #     op_enum_val = getattr(Op, mnemonic)
    #     opcode = int(op_enum_val)

    #     # === FORMAT: ZERO (Bijv. HALT, NOP, CLOSE, IOSYNC) ===
    #     if op_enum_val in FORMAT_ZERO:
    #         machine_code.append(opcode)
    #         continue

    #     # === FORMAT: ONE_ADDR (Bijv. JMP, JMPF, SUCCES, FAIL) ===
    #     if op_enum_val in FORMAT_ONE_ADDR:
    #         if len(parts) < 2:
    #             raise SyntaxError(f"Instructie '{mnemonic}' verwacht een adres/label op adres {current_address}")
    #         target = parts[1].upper()
            
    #         # Check of het argument een label is, anders aannemen dat het een getal is
    #         addr = labels[target] if target in labels else int(target)
    #         val = addr * 100 + opcode
    #         machine_code.append(val)
    #         continue

    #     # === FORMAT: ONE_REG (Bijv: INC K of DEC A of RETURN A) ===
    #     if op_enum_val in FORMAT_ONE_REG:
    #         if len(parts) < 2:
    #             raise SyntaxError(f"Instructie '{mnemonic}' verwacht een register op adres {current_address}")
    #         reg1_str = parts[1].upper()
    #         if reg1_str not in REGISTERS:
    #             raise SyntaxError(f"Onbekend register '{reg1_str}' op adres {current_address}")
    #         reg1 = REGISTERS[reg1_str]
            
    #         val = reg1 * 100 + opcode
    #         machine_code.append(val)
    #         continue

    #     # === FORMAT: TWO_REG_REG en TWO_REG_VAL (LDI, ADD, STO, CONTEXT, etc.) ===
    #     if op_enum_val in FORMAT_TWO_REG_REG or op_enum_val in FORMAT_TWO_REG_VAL:
    #         if len(parts) < 3:
    #             raise SyntaxError(f"Instructie '{mnemonic}' verwacht minimaal 2 argumenten op adres {current_address}")
            
    #         reg1_str = parts[1].upper()
    #         if reg1_str not in REGISTERS:
    #             raise SyntaxError(f"Onbekend register '{reg1_str}' op adres {current_address}")
    #         reg1 = REGISTERS[reg1_str]

    #         arg2_str = parts[2].upper()
            
    #         # Is het tweede argument een register? (Bijv. ADD A B)
    #         if arg2_str in REGISTERS:
    #             reg2 = REGISTERS[arg2_str]
    #             val = (reg2 * 10 + reg1) * 100 + opcode
    #         else:
    #             # Het is een waarde, IO-poort of label (Bijv. LDI A 42, CONTEXT A THREAD_START)
    #             arg2 = labels[arg2_str] if arg2_str in labels else int(arg2_str)
    #             val = (arg2 * 10 + reg1) * 100 + opcode

    #         machine_code.append(val)
    #         continue

    #     # Als er een opcode door de mazen van de wet glipt:
    #     raise SyntaxError(f"Instructie '{mnemonic}' is niet gekoppeld aan een bekend formaat op adres {current_address}")

    # return machine_code

    # --- STAP 3: PASS 2 - Vertalen naar STERN Machinecode ---
    machine_code = []

    for current_address, line in enumerate(instruction_lines):
        # Haal komma's weg en splits op whitespaces
        parts = line.replace(',', ' ').split()
        mnemonic = parts[0].upper()
        
        if not hasattr(Op, mnemonic):
            raise SyntaxError(f"Onbekende instructie '{mnemonic}' op adres {current_address}")
        
        op_enum_val = getattr(Op, mnemonic)
        opcode = int(op_enum_val)

        # === FORMAT: ZERO (Bijv. HALT, NOP, CLOSE, IOSYNC) ===
        if op_enum_val in FORMAT_ZERO:
            if len(parts) != 1:
                raise SyntaxError(f"Instructie '{mnemonic}' verwacht GEEN argumenten op adres {current_address} (gekregen: {len(parts)-1})")
            machine_code.append(opcode)
            continue

        # === FORMAT: ONE_ADDR (Bijv. JMP, JMPF, SUCCES, FAIL) ===
        if op_enum_val in FORMAT_ONE_ADDR:
            if len(parts) != 2:
                raise SyntaxError(f"Instructie '{mnemonic}' verwacht exact 1 adres/label op adres {current_address} (gekregen: {len(parts)-1})")
            target = parts[1].upper()
            
            addr = labels[target] if target in labels else int(target)
            val = addr * 100 + opcode
            machine_code.append(val)
            continue

        # === FORMAT: ONE_REG (Bijv: INC K of DEC A of RETURN A) ===
        if op_enum_val in FORMAT_ONE_REG:
            if len(parts) != 2:
                raise SyntaxError(f"Instructie '{mnemonic}' verwacht exact 1 register op adres {current_address} (gekregen: {len(parts)-1})")
            reg1_str = parts[1].upper()
            if reg1_str not in REGISTERS:
                raise SyntaxError(f"Onbekend register '{reg1_str}' op adres {current_address}")
            reg1 = REGISTERS[reg1_str]
            
            val = reg1 * 100 + opcode
            machine_code.append(val)
            continue

        # === FORMAT: TWO_REG_REG en TWO_REG_VAL (LDI, ADD, STO, CONTEXT, etc.) ===
        if op_enum_val in FORMAT_TWO_REG_REG or op_enum_val in FORMAT_TWO_REG_VAL:
            if len(parts) != 3:
                raise SyntaxError(f"Instructie '{mnemonic}' verwacht exact 2 argumenten op adres {current_address} (gekregen: {len(parts)-1})")
            
            reg1_str = parts[1].upper()
            if reg1_str not in REGISTERS:
                raise SyntaxError(f"Onbekend register '{reg1_str}' op adres {current_address}")
            reg1 = REGISTERS[reg1_str]

            arg2_str = parts[2].upper()
            
            # Is het tweede argument een register? (Bijv. ADD A B)
            if arg2_str in REGISTERS:
                # Extra check: Als het formaat uitsluitend een DIRECTE WAARDE vereist, kun je hier optioneel nog strenger valideren
                reg2 = REGISTERS[arg2_str]
                val = (reg2 * 10 + reg1) * 100 + opcode
            else:
                # Het is een waarde, IO-poort of label (Bijv. LDI A 42, CONTEXT A THREAD_START)
                try:
                    arg2 = labels[arg2_str] if arg2_str in labels else int(arg2_str)
                except ValueError:
                    raise SyntaxError(f"Ongeldig tweede argument '{arg2_str}' (geen register, label of integer) op adres {current_address}")
                val = (arg2 * 10 + reg1) * 100 + opcode

            machine_code.append(val)
            continue

        raise SyntaxError(f"Instructie '{mnemonic}' is niet gekoppeld aan een bekend formaat op adres {current_address}")

    return machine_code