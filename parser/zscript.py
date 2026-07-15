#!/usr/bin/env python3
import argparse
import os
import sys
from lark import Lark

# Importeer de benodigdheden uit je bestaande bestanden
from grammer import grammar
from assemblerV3 import assemble
from ZSparser import MacroExpander

def main():
    parser = argparse.ArgumentParser(
        description="ZScript Compiler & Assembler (ZScript -> STERN Machinecode)"
    )
    
    # Input bestand (verplicht, vereist .zs)
    parser.add_argument(
        "input_file", 
        help="Het ZScript bronbestand (.zs) dat verwerkt moet worden."
    )
    
    # Output bestand (optioneel)
    parser.add_argument(
        "-o", "--output", 
        help="De naam van het uitvoerbestand. Indien weggelaten, wordt de invoernaam met de juiste extensie gebruikt."
    )
    
    # Nu met 'ast' als extra optie!
    parser.add_argument(
        "--format", 
        choices=["asm", "bin", "ast"], 
        default="bin",
        help="De gewenste output: 'asm' (assembly), 'bin' (machinecode) of 'ast' (Abstract Syntax Tree). Standaard is 'bin'."
    )

    args = parser.parse_args()

    # 1. Controleer of het bestand bestaat en de juiste extensie heeft
    if not os.path.exists(args.input_file):
        print(f"Fout: Invoerbestand '{args.input_file}' bestaat niet.", file=sys.stderr)
        sys.exit(1)

    if not args.input_file.endswith(".zs"):
        print(f"Fout: Invoerbestand moet de extensie '.zs' hebben.", file=sys.stderr)
        sys.exit(1)

    # Bepaal de basisnaam voor het genereren van de standaard outputnaam
    base_name, _ = os.path.splitext(args.input_file)

    try:
        # 2. Lees de ZScript-broncode in
        with open(args.input_file, "r") as f:
            source_code = f.read()

        # 3. Parse de ZScript-code met Lark
        lark_parser = Lark(grammar, parser='lalr')
        parse_tree = lark_parser.parse(source_code)
        
        # === FORMAT: AST ===
        # Als de gebruiker de AST wil, slaan we de transformatie en assemblage over
        if args.format == "ast":
            output_file = args.output if args.output else f"{base_name}.ast"
            with open(output_file, "w") as f:
                # pretty() maakt een prachtige, ingesprongen tekstboom van de AST
                f.write(parse_tree.pretty())
            print(f"Abstract Syntax Tree (AST) succesvol opgeslagen in: {output_file}")
            return

        # 4. Voer de macro-expander uit (voor asm en bin)
        expander = MacroExpander()
        schone_assembly = expander.transform(parse_tree)

        # === FORMAT: ASM ===
        if args.format == "asm":
            output_file = args.output if args.output else f"{base_name}.asm"
            with open(output_file, "w") as f:
                f.write(schone_assembly)
            print(f"Preprocessed assembly succesvol opgeslagen in: {output_file}")

        # === FORMAT: BIN ===
        elif args.format == "bin":
            # Vertaal de schone assembly naar de lijst met integers via je assembler
            machine_code = assemble(schone_assembly)
            
            output_file = args.output if args.output else f"{base_name}.bin"
            with open(output_file, "w") as f:
                # Schrijf iedere waarde op een eigen regel
                for waarde in machine_code:
                    f.write(f"{waarde}\n")
            print(f"Machinecode (één waarde per regel) succesvol opgeslagen in: {output_file}")

    except Exception as e:
        print(f"Compilatie mislukt wegens een fout:\n{e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()