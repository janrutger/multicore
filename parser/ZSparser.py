from lark import Lark, Transformer
from grammer import grammar
from assemblerV3 import assemble

class MacroExpander(Transformer):
    def __init__(self):
        super().__init__()
        self.macro_table = {}
        self.symbol_table = {}
        
        # Standaardwaarden conform jouw ontwerp
        self.memsize = 1024
        self.sp_size = 0  # Default is 0 als er geen SP directive is
        
        # We berekenen de start van de data-allocatie zodra we MEMSIZE en SP weten.
        self.allocator_initialized = False
        self.next_free_address = None
        self.start_label = None
        self.loop_counter = 0           # Voor unieke lus-labels met REPEAT
        self.macro_call_counter = 0     # voor unike lus-labels in MARCO's

    def _initialize_allocator(self):
        if not self.allocator_initialized:
            # De stackpointer start op memsize - 1 (bijv. 1023)
            # De stack zelf heeft een omvang van self.sp_size
            # Het eerste veilige adres voor variabelen (RES) ligt direct daaronder:
            self.next_free_address = (self.memsize - 1) - self.sp_size
            self.allocator_initialized = True
            print(f"[ZScript] Geheugen geconfigureerd: MEMSIZE={self.memsize}, STACK_SIZE={self.sp_size}")
            print(f"[ZScript] Data Segment (RES) start vanaf adres: {self.next_free_address} (groeit omlaag)")

    def memsize_stmt(self, items):
        self.memsize = int(items[0])
        return None

    def sp_stmt(self, items):
        self.sp_size = int(items[0])
        return None

    def io_stmt(self, items):
        name = str(items[0])
        value = int(items[1])
        self.symbol_table[name] = {"type": "IO", "value": value}
        return None

    def const_stmt(self, items):
        name = str(items[0])
        value = int(items[1])
        self.symbol_table[name] = {"type": "CONST", "value": value}
        return None

    # --- DE NIEUWE NEERWAARTSE RES ALLOCATOR ---
    def res_stmt(self, items):
        # Zorg dat we weten wat MEMSIZE en SP zijn voordat we de eerste RES alloceren
        self._initialize_allocator()

        name = str(items[0])
        size = int(items[1]) # Hoeveel opeenvolgende adressen we reserveren
        
        # Als we 'size' adressen omlaag reserveren, is het laagste (start)adres:
        assigned_address = self.next_free_address - size + 1
        
        # Sla op in de symbol table
        self.symbol_table[name] = {"type": "RES", "value": assigned_address, "size": size}
        
        # Het volgende vrije adres schuift nu permanent omlaag, voorbij dit gereserveerde blok
        self.next_free_address -= size
        
        print(f"[ZScript Allocator] RES '{name}' (grootte {size}) -> Toegewezen op virtueel bereik: Adres {assigned_address} t/m {assigned_address + size - 1}")
        return None

    # Zorg dat we de allocator ook initialiseren als er GEEN RES-statements zijn
    def start(self, items):
        self._initialize_allocator()
        program_code = items[1]
        
        # Vervang alle bekende symbolen door hun berekende waarde
        for symbol, info in self.symbol_table.items():
            actual_value = str(info["value"])
            import re
            program_code = re.sub(rf'\b{symbol}\b', actual_value, program_code)
            
        # NIEUW: Als er een START directive is gedefinieerd, zetten we een JMP op adres 0
        if self.start_label:
            bootstrap = f"; --- BOOTSTRAP VECTOR ---\n    JMP {self.start_label}\n; ------------------------\n"
            program_code = bootstrap + program_code
            
        return program_code

    def start_stmt(self, items):
        # Sla het label op (bijvoorbeeld 'main')
        self.start_label = str(items[0]).upper()
        return None

    def macro_def(self, items):
        macro_name = str(items[0])
        remaining = items[1:]
        
        if remaining and isinstance(remaining[0], list):
            params = remaining[0]
            instructions = remaining[1:]
        else:
            params = []
            instructions = remaining

        clean_instructions = [str(instr) for instr in instructions if instr]

        self.macro_table[macro_name] = {
            "params": params,
            "body": clean_instructions
        }
        return None

    def param_list(self, items):
        return [str(i) for i in items]

    def instruction(self, items):
        mnemonic = str(items[0])
        args = [str(item) for item in items[1:] if item is not None]
        
        if args:
            return f"    {mnemonic} {', '.join(args)}"
        return f"    {mnemonic}"

    def label_def(self, items):
        return f"\n{items[0]}:"

    # def macro_call(self, items):
    #     macro_name = str(items[0])
    #     args = items[1] if len(items) > 1 else []

    #     if macro_name not in self.macro_table:
    #         raise NameError(f"Fout: Macro '{macro_name}' is niet gedefinieerd!")

    #     macro = self.macro_table[macro_name]
        
    #     if len(args) != len(macro["params"]):
    #         raise ValueError(f"Fout: {macro_name} verwacht {len(macro['params'])} args, kreeg {len(args)}.")

    #     param_map = dict(zip(macro["params"], args))
    #     expanded_lines = [f"; --- Start macro: {macro_name} ---"]

    #     for instr in macro["body"]:
    #         tokens = instr.replace(',', ' ').split()
    #         if not tokens:
    #             continue
    #         mnemonic = tokens[0]
    #         replaced_args = [param_map.get(tok, tok) for tok in tokens[1:]]
            
    #         if replaced_args:
    #             expanded_lines.append(f"    {mnemonic} {', '.join(replaced_args)}")
    #         else:
    #             expanded_lines.append(f"    {mnemonic}")
            
    #     expanded_lines.append(f"; --- Einde macro: {macro_name} ---")
    #     return "\n".join(expanded_lines)
    def macro_call(self, items):
        macro_name = str(items[0])
        args = items[1] if len(items) > 1 else []

        if macro_name not in self.macro_table:
            raise NameError(f"Fout: Macro '{macro_name}' is niet gedefinieerd!")

        macro = self.macro_table[macro_name]
        
        if len(args) != len(macro["params"]):
            raise ValueError(f"Fout: {macro_name} verwacht {len(macro['params'])} args, kreeg {len(args)}.")

        # Verhoog de unieke macro-aanroep ID om clashes te voorkomen
        self.macro_call_counter += 1
        unique_id = self.macro_call_counter

        param_map = dict(zip(macro["params"], args))
        expanded_lines = [f"; --- Start hygiënische macro: {macro_name} (ID: {unique_id}) ---"]

        for instr in macro["body"]:
            # Zorg dat we labels binnen de macro herkennen en uniek maken!
            # Labels eindigen vaak op een dubbele punt (bijv. 'LUS:')
            stripped_instr = instr.strip()
            if stripped_instr.endswith(':'):
                local_label = stripped_instr[:-1]
                # Maak het label uniek door de macro-call ID eraan te plakken
                hygienic_label = f"__M{unique_id}_{local_label}"
                expanded_lines.append(f"{hygienic_label}:")
                continue

            # Vervang tokens en parameters
            tokens = instr.replace(',', ' ').split()
            if not tokens:
                continue
            
            mnemonic = tokens[0]
            replaced_args = []
            
            for tok in tokens[1:]:
                # 1. Is het een parameter van de macro?
                if tok in param_map:
                    replaced_args.append(param_map[tok])
                # 2. Is het een verwijzing naar een lokaal label?
                # Als de macro springt naar 'LUS', dan mappen we dat naar '__M{id}_LUS'
                elif tok in [b.strip().replace(':', '') for b in macro["body"] if b.strip().endswith(':')]:
                    replaced_args.append(f"__M{unique_id}_{tok}")
                else:
                    replaced_args.append(tok)
            
            if replaced_args:
                expanded_lines.append(f"    {mnemonic} {', '.join(replaced_args)}")
            else:
                expanded_lines.append(f"    {mnemonic}")
            
        expanded_lines.append(f"; --- Einde macro: {macro_name} ---")
        return "\n".join(expanded_lines)
    
    # --- DE REPEAT GENERATOR ---

    
    def repeat_tail(self, items):
        # Filter haakjes of andere onnodige leestekens direct weg
        clean_items = [str(x) for x in items if str(x) not in ("(", ")")]
        
        # We kijken naar de resterende nuttige argumenten:
        if len(clean_items) == 3:
            # Variant: REGISTER TIMES_KEYWORD (INT | IDENTIFIER)
            # Voorbeeld: ['I', 'TIMES', '5']
            return {
                "mode": "TIMES",
                "reg": clean_items[0],
                "count": clean_items[2]
            }
        elif len(clean_items) == 4:
            # Variant: UNTIL_KEYWORD argument COMPARATOR argument
            # Voorbeeld: ['UNTIL', 'A', '==', '10']
            return {
                "mode": "UNTIL",
                "arg1": clean_items[1],
                "op": clean_items[2],
                "arg2": clean_items[3]
            }
        elif len(clean_items) == 7:
            # Variant: REGISTER TIMES_KEYWORD (INT | IDENTIFIER) UNTIL_KEYWORD argument COMPARATOR argument
            # Voorbeeld: ['K', 'TIMES', '10', 'UNTIL', 'B', '==', '1']
            return {
                "mode": "BOTH",
                "reg": clean_items[0],
                "count": clean_items[2],
                "arg1": clean_items[4],
                "op": clean_items[5],
                "arg2": clean_items[6]
            }
        
        # Mocht de lengte afwijken, geef de rauwe lijst terug voor de fallback-handler
        return {"error": True, "raw_items": clean_items}

    def repeat_stmt(self, items):
        tail = None
        body_lines = []
        
        for item in items:
            # Als het item de getransformeerde dict van repeat_tail is
            if isinstance(item, dict) and "mode" in item:
                tail = item
            # Soms geeft Lark de getransformeerde node door als een Tree-object
            elif hasattr(item, 'data') and item.data == 'repeat_tail':
                tail = self.repeat_tail(item.children)
            elif isinstance(item, str):
                if item != "REPEAT":
                    body_lines.append(item)
            elif isinstance(item, list):
                body_lines.extend([str(x) for x in item if x])
            else:
                # Fallback voor overige Lark elementen/tokens
                val_str = str(item)
                if val_str.strip() and val_str != "REPEAT":
                    body_lines.append(val_str)

        # WATERDICHTE DEBUGGER:
        if not tail or "error" in tail:
            print("\n[DEBUG ERROR] REPEAT detectie mislukt!")
            print(f"Binnengekomen items in repeat_stmt (aantal: {len(items)}):")
            for idx, it in enumerate(items):
                if hasattr(it, 'data'):
                    print(f"  [{idx}] Lark Tree Node: data={it.data}, children={it.children}")
                else:
                    print(f"  [{idx}] Type={type(it)}, Waarde={repr(it)}")
            raise ValueError("Fout: Geen geldige REPEAT conditie gevonden!")

        # Genereer unieke labels voor deze specifieke lus
        start_label = f"__REP_START_{self.loop_counter}"
        end_label = f"__REP_END_{self.loop_counter}"
        self.loop_counter += 1

        assembly = []

        # === 1. INITIALISATIE (Voorafgaand aan de lus) ===
        if tail["mode"] in ["TIMES", "BOTH"]:
            assembly.append(f"    LDI {tail['reg']}, {tail['count']}")

        # === 2. DE LUS IN ===
        assembly.append(f"; --- REPEAT LOOP START ---")
        assembly.append(f"{start_label}:")

        # Voeg de body-instructies toe
        for line in body_lines:
            assembly.append(line)

        # === 3. EVALUATIE (Aan het einde van de lus) ===
        if tail["mode"] == "UNTIL":
            if tail["op"] == "==":
                assembly.append(f"    TSTE {tail['arg1']}, {tail['arg2']}")
            elif tail["op"] == ">":
                assembly.append(f"    TSTG {tail['arg1']}, {tail['arg2']}")
            assembly.append(f"    JMPF {start_label}")

        elif tail["mode"] == "TIMES":
            # Verminder de teller met 1 (bijv. DEC I)
            assembly.append(f"    DEC {tail['reg']}")
            # Test direct of de teller 0 is geworden (TSTZ I)
            assembly.append(f"    TSTZ {tail['reg']}")
            # Indien NIET nul (False), spring terug naar het begin
            assembly.append(f"    JMPF {start_label}")

        elif tail["mode"] == "BOTH":
            # Eerst de UNTIL ontsnapping testen
            if tail["op"] == "==":
                assembly.append(f"    TSTE {tail['arg1']}, {tail['arg2']}")
            elif tail["op"] == ">":
                assembly.append(f"    TSTG {tail['arg1']}, {tail['arg2']}")
            assembly.append(f"    JMPT {end_label}")

            # Daarna de teller decrementeren en testen
            assembly.append(f"    DEC {tail['reg']}")
            assembly.append(f"    TSTZ {tail['reg']}")
            # Indien nog niet 0 (False), herhaal de lus
            assembly.append(f"    JMPF {start_label}")

        # === 4. HET EINDE ===
        if tail["mode"] == "BOTH":
            assembly.append(f"{end_label}:")
        
        assembly.append(f"; --- REPEAT LOOP END ---")

        return "\n".join(assembly)
    

    def arg_list(self, items):
        return [str(i) for i in items]

    def map_block(self, items):
        return None

    def program_block(self, items):
        # We filteren lege regels eruit en voegen ze samen
        lines = [str(item) for item in items if item and str(item) != 'None']
        
        # Schoonheidsreparatie: we zorgen dat dubbele witregels (door labels) 
        # netjes worden gereduceerd tot één schone witregel.
        raw_code = "\n".join(lines)
        import re
        clean_code = re.sub(r'\n{3,}', '\n\n', raw_code)
        return clean_code