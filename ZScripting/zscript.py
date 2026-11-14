#!/usr/bin/env python3
import argparse
import os
import sys
import re
from lark import Lark

# Importeer de benodigdheden uit je bestaande bestanden
from grammer import grammar
from assemblerV3 import assemble
from ZSparser import ZScriptExpander as MacroExpander


def resolve_macro_includes(source_code, source_file_path, library_name="std_macros.zs"):
    """
    Scant naar 'INCLUDE macro1, macro2' en injecteert uitsluitend 
    de gevraagde macro-definities uit het centrale macro-bestand.
    Zoekt transparant in de map van het .zs bestand óf de huidige werkmap.
    """
    # 1. Bepaal het zoekpad: eerst in de map van het bronbestand, dan lokaal
    source_dir = os.path.dirname(os.path.abspath(source_file_path))
    library_path = os.path.join(source_dir, library_name)

    # Fallback naar huidige werkomgeving als hij niet in de submap staat
    if not os.path.exists(library_path):
        library_path = library_name

    # 2. Controleer of het macro-bestand bestaat zodra er een INCLUDE statement is
    if not os.path.exists(library_path):
        if "INCLUDE" in source_code:
            raise FileNotFoundError(
                f"\n[ZScript Preprocessor Fout] Macro-bibliotheek '{library_name}' niet gevonden!\n"
                f"Gezocht op pad: '{os.path.abspath(library_path)}'"
            )
        return source_code

    # 3. Lees alle macro's in uit het centrale bestand
    with open(library_path, "r", encoding="utf-8") as f:
        lib_content = f.read()

    # Extraheer alle MACRO definities met hun inhoud
    macro_pattern = r'(MACRO\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{[^}]*\})'
    available_macros = {}
    for full_macro, macro_name in re.findall(macro_pattern, lib_content, re.DOTALL):
        available_macros[macro_name] = full_macro

    # 4. Zoek alle INCLUDE regels in het bronbestand
    include_line_pattern = r'^\s*INCLUDE\s+([a-zA-Z0-9_,\s]+)$'
    
    def process_include(match):
        raw_names = match.group(1)
        # Filter leeg, spaties en eventueel dubbelgeschreven 'INCLUDE' eruit
        requested_names = [
            name.strip() for name in re.split(r'[,\s]+', raw_names) 
            if name.strip() and name.strip().upper() != 'INCLUDE'
        ]
        
        extracted_code = []
        for name in requested_names:
            if name in available_macros:
                extracted_code.append(f"    ; --- INCLUDED MACRO: {name} ---")
                extracted_code.append(available_macros[name])
                print(f"[ZScript Preprocessor Load] Macro '{name}' succesvol geladen uit '{library_name}'")
            else:
                raise NameError(f"[ZScript Preprocessor Fout] Macro '{name}' niet gevonden in '{library_path}'!")
        
        return "\n".join(extracted_code)

    # Gebruik re.MULTILINE zodat ^ en $ echt per regel werken
    processed_source = re.sub(include_line_pattern, process_include, source_code, flags=re.MULTILINE | re.IGNORECASE)
    return processed_source

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
        with open(args.input_file, "r", encoding="utf-8") as f:
            raw_source = f.read()

        # 2b. Resolveer de macro includes (zoekt automatisch in de map van het .zs bestand!)
        source_code = resolve_macro_includes(raw_source, source_file_path=args.input_file, library_name="std_macros.zs")

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