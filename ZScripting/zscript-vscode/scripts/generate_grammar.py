#!/usr/bin/env python3
"""
===============================================================================
 STERN-Z32 PLATFORM: VS CODE ZSCRIPT GRAMMAR GENERATOR
===============================================================================
 Genereert automatisch de VS Code TextMate grammatica (stern-asm.tmLanguage.json)
 direct uit de hardware-definities van de SternZ32G processor (opcodes.py) en 
 de ZScript grammatica (grammer.py).
===============================================================================
"""

import json
import os
import sys
import re

# =============================================================================
# STERN-Z32 AUTOMATISCHE PAD-DETECTIE
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))               # .../zscript-vscode/scripts
EXTENSION_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))      # .../zscript-vscode
ZSCRIPTING_ROOT = os.path.abspath(os.path.join(EXTENSION_ROOT, '..'))  # .../ZScripting
MULTICORE_ROOT = os.path.abspath(os.path.join(ZSCRIPTING_ROOT, '..'))  # .../git/Multicore

# Voeg de paden naar sys.path toe zodat Python 'opcodes' en 'grammer' altijd direct vindt:
STERN_CORE_DIR = os.path.join(MULTICORE_ROOT, "SternZ32A")  # /home/janrutger/git/Multicore/SternZ32A

sys.path.insert(0, STERN_CORE_DIR)
sys.path.insert(0, ZSCRIPTING_ROOT)
sys.path.insert(0, EXTENSION_ROOT)

# =============================================================================
# IMPORTEER STERN-Z32 PLATFORM DEFINITIES
# =============================================================================
try:
    from opcodes import Op, Reg
    from grammer import grammar
except ImportError as e:
    print(f"\n[ERROR] Kan SternZ32 definities niet laden: {e}", file=sys.stderr)
    print(f"[DIAGNOSE] Gezochte zoekpaden (sys.path):", file=sys.stderr)
    for p in sys.path[:5]:
        print(f"  - {p}", file=sys.stderr)
    print("\nControleer of 'opcodes.py' in SternZ32A staat en 'grammer.py' in ZScripting.\n", file=sys.stderr)
    sys.exit(1)


def extract_zscript_keywords():
    """Extraheert alle ZScript trefwoorden direct uit de Lark-grammatica."""
    kw_matches = re.findall(r'_?[A-Z0-9_]+\.2:\s*"([A-Z0-9_]+)"', grammar)
    
    base_keywords = {
        "MAP", "MEMORY", "PROGRAM", "SHARED", "PRIVATE", "START", "CONST", "IO", "SP", 
        "RES", "SRES", "PRES", "MACRO", "REPEAT", "TIMES", "UNTIL", "IF", "ELSE", "INCLUDE",
        "TRUE", "FALSE", "ZERO", "SPAWN", "UPDATE", "HARVEST", "WRITE", "READ", "ATOMIC"
    }
    
    all_keywords = base_keywords.union(set(kw_matches))
    return sorted(list(all_keywords), key=str.lower)


def extract_mnemonics():
    """Extraheert alle hardware mnemonics (opcodes) direct uit Op Enum."""
    mnemonics = [op.name for op in Op]
    return sorted(list(set(mnemonics)), key=str.lower)


def extract_registers():
    """Extraheert alle registers (A, B, C... I) uit Reg Enum."""
    registers = [reg.name for reg in Reg]
    registers.extend([f"R{i}" for i in range(10)])
    registers.extend(["PC", "SP"])
    return sorted(list(set(registers)), key=str.lower)


def generate_vscode_grammar(template_path, output_path):
    """Vervangt de placeholders in de TextMate template door gegenereerde RegEx patronen."""
    print("[BUILD] Extraheren van SternZ32 & ZScript definities...")

    keywords = extract_zscript_keywords()
    mnemonics = extract_mnemonics()
    registers = extract_registers()

    print(f" -> {len(keywords)} ZScript Directives/Keywords geladen.")
    print(f" -> {len(mnemonics)} Hardware Mnemonics geladen uit opcodes.py.")
    print(f" -> {len(registers)} Registers geladen.")

    # Opbouwen van RegEx patronen
    directive_regex = f"(?i)\\b({'|'.join(keywords)})\\b"
    instruction_regex = f"(?i)\\b({'|'.join(mnemonics)})\\b"
    register_regex = f"(?i)\\b({'|'.join(registers)})\\b"

    if not os.path.exists(template_path):
        print(f"[ERROR] Template bestand niet gevonden op: {template_path}", file=sys.stderr)
        sys.exit(1)

    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # JSON Escaping voor backslashes (\b -> \\b)
    escaped_directive = directive_regex.replace('\\', '\\\\')
    escaped_instruction = instruction_regex.replace('\\', '\\\\')
    escaped_register = register_regex.replace('\\', '\\\\')

    # Injecteer de regex patronen in het sjabloon
    grammar_content = template_content.replace("%%DIRECTIVE_REGEX%%", escaped_directive)
    grammar_content = grammar_content.replace("%%INSTRUCTION_REGEX%%", escaped_instruction)
    grammar_content = grammar_content.replace("%%REGISTER_REGEX%%", escaped_register)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(grammar_content)

    print(f"[SUCCESS] VS Code grammatica succesvol gegenereerd op:\n -> {output_path}")


if __name__ == "__main__":
    template_file = os.path.join(EXTENSION_ROOT, 'syntaxes', 'stern-asm.tmLanguage.template.json')
    output_file = os.path.join(EXTENSION_ROOT, 'syntaxes', 'stern-asm.tmLanguage.json')

    generate_vscode_grammar(template_file, output_file)