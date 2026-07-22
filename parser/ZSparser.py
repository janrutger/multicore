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

    #     self.macro_call_counter += 1
    #     unique_id = self.macro_call_counter

    #     param_map = dict(zip(macro["params"], args))
    #     expanded_lines = [f"; --- Start hygiënische macro: {macro_name} (ID: {unique_id}) ---"]

    #     for instr in macro["body"]:
    #         stripped_instr = instr.strip()
    #         if stripped_instr.endswith(':'):
    #             local_label = stripped_instr[:-1]
    #             hygienic_label = f"__M{unique_id}_{local_label}"
    #             expanded_lines.append(f"{hygienic_label}:")
    #             continue

    #         # Vervang tokens en parameters
    #         tokens = instr.replace(',', ' ').split()
    #         if not tokens:
    #             continue
            
    #         mnemonic = tokens[0]
    #         replaced_args = []
            
    #         for tok in tokens[1:]:
    #             if tok in param_map:
    #                 replaced_args.append(param_map[tok])
    #             elif tok in [b.strip().replace(':', '') for b in macro["body"] if b.strip().endswith(':')]:
    #                 replaced_args.append(f"__M{unique_id}_{tok}")
    #             else:
    #                 replaced_args.append(tok)
            
    #         # === AUTOMATISCHE TYPE-CORRECTIE VÓÓR EMISSIE (FIXED) ===
    #         if mnemonic == "LD" and len(replaced_args) == 2:
    #             source_val = replaced_args[1]
                
    #             # Check of het direct een getal is
    #             is_immediate = source_val.isdigit() or source_val.startswith('-')
                
    #             # FIX: Check of het een symbool is dat resolvet naar een getal (CONST / IO / RES)
    #             if not is_immediate and source_val in self.symbol_table:
    #                 resolved_value = str(self.symbol_table[source_val]["value"])
    #                 if resolved_value.isdigit() or resolved_value.startswith('-'):
    #                     is_immediate = True
                        
    #             if is_immediate:
    #                 mnemonic = "LDI"

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

        self.macro_call_counter += 1
        unique_id = self.macro_call_counter

        param_map = dict(zip(macro["params"], args))
        expanded_lines = [f"; --- Start hygiënische macro: {macro_name} (ID: {unique_id}) ---"]

        # Splits de body op regeleinden voor het geval er getransformeerde blokken (zoals REPEAT) in zitten
        raw_body_lines = []
        for raw_item in macro["body"]:
            for sub_line in str(raw_item).splitlines():
                if sub_line.strip():
                    raw_body_lines.append(sub_line)

        for instr in raw_body_lines:
            stripped_instr = instr.strip()
            
            # 1. Bewaar commentaren EN automatisch gegenereerde REPEAT/PIPE labels intact!
            if stripped_instr.startswith(';') or stripped_instr.startswith('__REP') or stripped_instr.startswith('__PIPE'):
                expanded_lines.append(f"    {stripped_instr}" if not stripped_instr.endswith(':') else f"{stripped_instr}")
                continue

            # 2. Lokale macro-labels prefixen met __M<id>_
            if stripped_instr.endswith(':'):
                local_label = stripped_instr[:-1]
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
                if tok in param_map:
                    replaced_args.append(param_map[tok])
                elif tok in [b.strip().replace(':', '') for b in raw_body_lines if b.strip().endswith(':') and not b.strip().startswith('__REP')]:
                    replaced_args.append(f"__M{unique_id}_{tok}")
                else:
                    replaced_args.append(tok)
            
            # === AUTOMATISCHE TYPE-CORRECTIE VÓÓR EMISSIE ===
            if mnemonic == "LD" and len(replaced_args) == 2:
                source_val = replaced_args[1]
                is_immediate = source_val.isdigit() or source_val.startswith('-')
                
                if not is_immediate and source_val in self.symbol_table:
                    resolved_value = str(self.symbol_table[source_val]["value"])
                    if resolved_value.isdigit() or resolved_value.startswith('-'):
                        is_immediate = True
                        
                if is_immediate:
                    mnemonic = "LDI"

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

    # def repeat_stmt(self, items):
    #     tail = None
    #     body_lines = []
        
    #     for item in items:
    #         # Als het item de getransformeerde dict van repeat_tail is
    #         if isinstance(item, dict) and "mode" in item:
    #             tail = item
    #         # Soms geeft Lark de getransformeerde node door als een Tree-object
    #         elif hasattr(item, 'data') and item.data == 'repeat_tail':
    #             tail = self.repeat_tail(item.children)
    #         elif isinstance(item, str):
    #             if item != "REPEAT":
    #                 body_lines.append(item)
    #         elif isinstance(item, list):
    #             body_lines.extend([str(x) for x in item if x])
    #         else:
    #             # Fallback voor overige Lark elementen/tokens
    #             val_str = str(item)
    #             if val_str.strip() and val_str != "REPEAT":
    #                 body_lines.append(val_str)

    #     # WATERDICHTE DEBUGGER:
    #     if not tail or "error" in tail:
    #         print("\n[DEBUG ERROR] REPEAT detectie mislukt!")
    #         print(f"Binnengekomen items in repeat_stmt (aantal: {len(items)}):")
    #         for idx, it in enumerate(items):
    #             if hasattr(it, 'data'):
    #                 print(f"  [{idx}] Lark Tree Node: data={it.data}, children={it.children}")
    #             else:
    #                 print(f"  [{idx}] Type={type(it)}, Waarde={repr(it)}")
    #         raise ValueError("Fout: Geen geldige REPEAT conditie gevonden!")

    #     # Genereer unieke labels voor deze specifieke lus
    #     start_label = f"__REP_START_{self.loop_counter}"
    #     end_label = f"__REP_END_{self.loop_counter}"
    #     self.loop_counter += 1

    #     assembly = []

    #     # === 1. INITIALISATIE (Voorafgaand aan de lus) ===
    #     if tail["mode"] in ["TIMES", "BOTH"]:
    #         assembly.append(f"    LDI {tail['reg']}, {tail['count']}")

    #     # === 2. DE LUS IN ===
    #     assembly.append(f"; --- REPEAT LOOP START ---")
    #     assembly.append(f"{start_label}:")

    #     # Voeg de body-instructies toe
    #     for line in body_lines:
    #         assembly.append(line)

    #     # === 3. EVALUATIE (Aan het einde van de lus) ===
    #     if tail["mode"] == "UNTIL":
    #         if tail["op"] == "==":
    #             assembly.append(f"    TSTE {tail['arg1']}, {tail['arg2']}")
    #         elif tail["op"] == ">":
    #             assembly.append(f"    TSTG {tail['arg1']}, {tail['arg2']}")
    #         assembly.append(f"    JMPF {start_label}")

    #     elif tail["mode"] == "TIMES":
    #         # Verminder de teller met 1 (bijv. DEC I)
    #         assembly.append(f"    DEC {tail['reg']}")
    #         # Test direct of de teller 0 is geworden (TSTZ I)
    #         assembly.append(f"    TSTZ {tail['reg']}")
    #         # Indien NIET nul (False), spring terug naar het begin
    #         assembly.append(f"    JMPF {start_label}")

    #     elif tail["mode"] == "BOTH":
    #         # Eerst de UNTIL ontsnapping testen
    #         if tail["op"] == "==":
    #             assembly.append(f"    TSTE {tail['arg1']}, {tail['arg2']}")
    #         elif tail["op"] == ">":
    #             assembly.append(f"    TSTG {tail['arg1']}, {tail['arg2']}")
    #         assembly.append(f"    JMPT {end_label}")

    #         # Daarna de teller decrementeren en testen
    #         assembly.append(f"    DEC {tail['reg']}")
    #         assembly.append(f"    TSTZ {tail['reg']}")
    #         # Indien nog niet 0 (False), herhaal de lus
    #         assembly.append(f"    JMPF {start_label}")

    #     # === 4. HET EINDE ===
    #     if tail["mode"] == "BOTH":
    #         assembly.append(f"{end_label}:")
        
    #     assembly.append(f"; --- REPEAT LOOP END ---")

    #     return "\n".join(assembly)
    def repeat_stmt(self, items):
        tail = None
        body_lines = []
        
        for item in items:
            if isinstance(item, dict) and "mode" in item:
                tail = item
            elif hasattr(item, 'data') and item.data == 'repeat_tail':
                tail = self.repeat_tail(item.children)
            elif isinstance(item, str):
                if item != "REPEAT":
                    # Als de string meerdere regels bevat, splitsen we ze
                    body_lines.extend([line.strip() for line in item.splitlines() if line.strip()])
            elif isinstance(item, list):
                for x in item:
                    if x:
                        body_lines.extend([line.strip() for line in str(x).splitlines() if line.strip()])
            else:
                val_str = str(item)
                if val_str.strip() and val_str != "REPEAT":
                    body_lines.extend([line.strip() for line in val_str.splitlines() if line.strip()])

        if not tail or "error" in tail:
            raise ValueError("Fout: Geen geldige REPEAT conditie gevonden!")

        start_label = f"__REP_START_{self.loop_counter}"
        end_label = f"__REP_END_{self.loop_counter}"
        self.loop_counter += 1

        assembly = []

        # 1. INITIALISATIE
        if tail["mode"] in ["TIMES", "BOTH"]:
            assembly.append(f"    LDI {tail['reg']}, {tail['count']}")

        # 2. DE LUS IN
        assembly.append(f"; --- REPEAT LOOP START ---")
        assembly.append(f"{start_label}:")

        for line in body_lines:
            if not line.startswith(";") and not line.endswith(":") and not line.startswith("    "):
                assembly.append(f"    {line}")
            else:
                assembly.append(line)

        # 3. EVALUATIE
        if tail["mode"] == "UNTIL":
            if tail["op"] == "==":
                assembly.append(f"    TSTE {tail['arg1']}, {tail['arg2']}")
            elif tail["op"] == ">":
                assembly.append(f"    TSTG {tail['arg1']}, {tail['arg2']}")
            assembly.append(f"    JMPF {start_label}")

        elif tail["mode"] == "TIMES":
            assembly.append(f"    DEC {tail['reg']}")
            assembly.append(f"    TSTZ {tail['reg']}")
            assembly.append(f"    JMPF {start_label}")

        elif tail["mode"] == "BOTH":
            if tail["op"] == "==":
                assembly.append(f"    TSTE {tail['arg1']}, {tail['arg2']}")
            elif tail["op"] == ">":
                assembly.append(f"    TSTG {tail['arg1']}, {tail['arg2']}")
            assembly.append(f"    JMPT {end_label}")

            assembly.append(f"    DEC {tail['reg']}")
            assembly.append(f"    TSTZ {tail['reg']}")
            assembly.append(f"    JMPF {start_label}")

        if tail["mode"] == "BOTH":
            assembly.append(f"{end_label}:")
        
        assembly.append(f"; --- REPEAT LOOP END ---")

        return "\n".join(assembly)
    
    # === FIX: Transformeer de mem_ref tree naar een herkenbare string ===
    def mem_ref(self, items):
        """
        Zet een Lark 'mem_ref' node om naar een string formaat dat 
        de assignment handler direct kan parsen, bijv: '[1008]' of '[1008 + B]'
        """
        if len(items) == 1:
            return f"[{items[0]}]"
        elif len(items) == 2:
            return f"[{items[0]} + {items[1]}]"
        return f"[{' '.join(str(x) for x in items)}]"


    # === GECORRIGEERDE ASSIGNMENT HANDLER ===
    def assignment(self, items):
        """
        Verwerkt de versimpelde ZScript dataflow syntax met correcte hardware-mapping.
        Formaat: van -> naar
        """
        source = str(items[0]).strip()
        target = str(items[1]).strip()
        asm_output = []

        def parse_memory_operand(operand):
            if operand.startswith('[') and operand.endswith(']'):
                inner = operand[1:-1].strip()
                if '+' in inner:
                    parts = inner.split('+')
                    base = parts[0].strip()
                    index = parts[1].strip()
                    return {"type": "INDEXED", "base": base, "index": index}
                else:
                    return {"type": "DIRECT", "address": inner}
            return {"type": "REGISTER_OR_VAL", "value": operand}

        src_parsed = parse_memory_operand(source)
        tgt_parsed = parse_memory_operand(target)

        # --- CASE 1: [adres + Ry] -> Rx (Geïndexeerd Geheugen Lezen) ---
        if src_parsed["type"] == "INDEXED" and tgt_parsed["type"] == "REGISTER_OR_VAL":
            dest_reg = tgt_parsed["value"]
            base_address = src_parsed["base"]
            index_reg = src_parsed["index"]

            if index_reg != 'I':
                asm_output.append(f"    LD I, {index_reg}")
            asm_output.append(f"    LDX {dest_reg}, {base_address}")

        # --- CASE 2: Rx -> [adres + Ry] (Geïndexeerd Geheugen Schrijven) ---
        elif src_parsed["type"] == "REGISTER_OR_VAL" and tgt_parsed["type"] == "INDEXED":
            src_reg = src_parsed["value"]
            base_address = tgt_parsed["base"]
            index_reg = tgt_parsed["index"]

            if index_reg != 'I':
                asm_output.append(f"    LD I, {index_reg}")
            asm_output.append(f"    STX {src_reg}, {base_address}")

        # --- CASE 3: [adres] -> Rx (Direct Geheugen Lezen) ---
        elif src_parsed["type"] == "DIRECT" and tgt_parsed["type"] == "REGISTER_OR_VAL":
            asm_output.append(f"    LDM {tgt_parsed['value']}, {src_parsed['address']}")

        # --- CASE 4: Rx -> [adres] (Direct Geheugen Schrijven) ---
        elif src_parsed["type"] == "REGISTER_OR_VAL" and tgt_parsed["type"] == "DIRECT":
            asm_output.append(f"    STO {src_parsed['value']}, {tgt_parsed['address']}")

        # --- CASE 5: Waarde/Register/Symbool -> Rx (Immediate laden of Register Transfer) ---
        elif src_parsed["type"] == "REGISTER_OR_VAL" and tgt_parsed["type"] == "REGISTER_OR_VAL":
            val = src_parsed["value"]
            
            # --- FIX: Controleer of het direct een getal is óf een bekend getal-symbool ---
            is_immediate = val.isdigit() or val.startswith('-')
            
            if not is_immediate and val in self.symbol_table:
                resolved = str(self.symbol_table[val]["value"])
                if resolved.isdigit() or resolved.startswith('-'):
                    is_immediate = True

            if is_immediate:
                asm_output.append(f"    LDI {tgt_parsed['value']}, {val}")
            else:
                asm_output.append(f"    LD {tgt_parsed['value']}, {val}")

        return "\n".join(asm_output)

    # PARALLEL statement block
    def parallel_stmt(self, items):
        """
        Genereert een hygiënische hardware-parallel loop met een Greedy JOIN voor de Z32 matrix.
        Werkt non-blocking via de asynchrone CONTEXT/JOIN architectuur.
        """
        # SCHOONMAAKFILTER: Eet alle syntactische ruis, haakjes en keywords op
        clean_items = [
            str(x) for x in items 
            if str(x) not in ("(", ")", "{", "}", "PARALLEL", "USING", "UNTIL", "->")
        ]

        # Controleer of we exact de 7 bouwstenen overhouden
        if len(clean_items) < 7:
            raise ValueError(f"[ZScript Error] PARALLEL syntaffout. Verwachtte 7 argumenten, kreeg: {clean_items}")

        worker_name = clean_items[0] # XOR_WORKER
        src_mem     = clean_items[1] # [INbuffer + X]
        rz_reg      = clean_items[2] # A
        comparator  = clean_items[3] # == of >
        rq_val      = clean_items[4] # B
        dest_reg    = clean_items[5] # A
        dest_mem    = clean_items[6] # [ENCODEbuffer + Y]

        # Helper om basisadres en index-register te splitsen
        def parse_memory_operand(operand):
            inner = operand.strip("[] ")
            if '+' in inner:
                parts = inner.split('+')
                return parts[0].strip(), parts[1].strip()
            return inner, None

        src_base, src_idx   = parse_memory_operand(src_mem)
        dest_base, dest_idx = parse_memory_operand(dest_mem)

        pipe_id = self.loop_counter
        self.loop_counter += 1

        # Unieke labels voor deze parallelle pijplijn
        lbl_loop    = f"__PIPE_{pipe_id}_LOOP"
        lbl_harvest = f"__PIPE_{pipe_id}_HARVEST"
        lbl_drain   = f"__PIPE_{pipe_id}_DRAIN"
        lbl_collect = f"__PIPE_{pipe_id}_COLLECT"
        lbl_done    = f"__PIPE_{pipe_id}_DONE"

        asm = [f"\n; --- START GEGENEREERDE HARDWARE PARALLEL (Worker: {worker_name}, ID: {pipe_id}) ---"]

        # --- 1. HOOFDLUS: Laad data in Rz via het index-register ---
        asm.append(f"{lbl_loop}:")
        if src_idx:
            if src_idx != 'I':
                asm.append(f"    LD I, {src_idx}")
            asm.append(f"    LDX {rz_reg}, {src_base}")
        else:
            asm.append(f"    LDM {rz_reg}, {src_base}")

        # Evalueer direct de UNTIL stop-conditie
        if comparator == "==":
            asm.append(f"    TSTE {rz_reg}, {rq_val}")
        elif comparator == ">":
            asm.append(f"    TSTG {rz_reg}, {rq_val}")
        asm.append(f"    JMPT {lbl_drain}")

        # --- 2. CONTEXT SPAWN (Inclusief Z32 matrix-vol check) ---
        asm.append(f"    CONTEXT {rz_reg}, {worker_name}") 
        asm.append(f"    FAIL {lbl_harvest}")  # Matrix vol (< 10 cores)? Spring naar verplicht oogsten.
        
        # Incrementeer de bron-pointer (asynchroon, mag direct tijdens het rekenen)
        if src_idx:
            asm.append(f"    INC {src_idx}")

        # === GREEDY JOIN INTERVALLUM ===
        # Probeer direct de oudste actieve thread te oogsten (non-blocking)
        asm.append(f"    JOIN {dest_reg}, {lbl_loop}")
        
        # Oogst gelukt (Fallthrough): Schrijf direct weg naar de ENCODEbuffer via dest_idx
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX {dest_reg}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {dest_reg}, {dest_base}")
        asm.append(f"    JMP {lbl_loop}")

        # --- 3. VERPLICHT OOGSTEN (Bij matrix-verzadiging) ---
        asm.append(f"{lbl_harvest}:")
        asm.append(f"    JOIN {dest_reg}, {lbl_harvest}") 
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX {dest_reg}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {dest_reg}, {dest_base}")
        asm.append(f"    JMP {lbl_loop}")

        # --- 4. LEEGDRAAI-FASE (Invoer is uitgeput, wachten op lopende cores) ---
        asm.append(f"{lbl_drain}:")
        asm.append(f"    SYNC {lbl_collect}")
        asm.append(f"    JMP {lbl_done}")

        asm.append(f"{lbl_collect}:")
        asm.append(f"    JOIN {dest_reg}, {lbl_collect}")
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX {dest_reg}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {dest_reg}, {dest_base}")
        asm.append(f"    JMP {lbl_drain}")

        # --- 5. AFSLUITING (Sluit de buffer netjes af met de stop-waarde) ---
        asm.append(f"{lbl_done}:")
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX {rq_val}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {rq_val}, {dest_base}")

        asm.append(f"; --- EINDE GEGENEREERDE HARDWARE PARALLEL ---\n")
        return "\n".join(asm)

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