import re 
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
        self.spawn_counter = 0          # Unieke teller voor SPAWN pijplijnen

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

    

    def macro_call(self, items):
        macro_name = str(items[0])
        args = items[1] if len(items) > 1 else []

        # === FIX VOOR LEGE ARGUMENTENLIJST ===
        if args is None:
            args = []
        # =====================================

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


# === GECORRIGEERDE SPAWN HANDLER (WATERDICHTE DRAIN PIJPLIJN) ===
    def spawn_stmt(self, items):
        self.spawn_counter += 1
        spawn_id = self.spawn_counter

        lbl_loop  = f"__SPAWN_{spawn_id}_LOOP"
        lbl_full  = f"__SPAWN_{spawn_id}_FULL"
        lbl_drain = f"__SPAWN_{spawn_id}_DRAIN"
        lbl_wait  = f"__SPAWN_{spawn_id}_DRAIN_WAIT"
        lbl_done  = f"__SPAWN_{spawn_id}_DONE"

        clean_items = [x for x in items if x is not None]

        worker_label = str(clean_items[1]).strip()
        input_reg    = str(clean_items[2]).strip()

        cond_item = clean_items[4]
        cond = None
        if isinstance(cond_item, dict):
            cond = cond_item
        elif hasattr(cond_item, 'children'):
            children = [str(c).strip() for c in cond_item.children]
            if "ZERO" in children or (len(children) >= 2 and children[1] == "ZERO"):
                cond = {"op": "ZERO", "reg": children[0]}
            elif "==" in children:
                cond = {"op": "==", "arg1": children[0], "arg2": children[2]}
            elif ">" in children:
                cond = {"op": ">", "arg1": children[0], "arg2": children[2]}

        if_mode = str(clean_items[5]).strip()

        update_idx = -1
        harvest_idx = -1
        for i, item in enumerate(clean_items):
            s = str(item).strip()
            if s == "UPDATE":
                update_idx = i
            elif s == "HARVEST":
                harvest_idx = i

        harvest_reg = str(clean_items[harvest_idx + 1]).strip()

        def extract_lines(slice_items):
            lines = []
            for item in slice_items:
                s = str(item).strip()
                if s in ("UPDATE", "HARVEST", "{", "}", "(", ")") or not s:
                    continue
                for line in str(item).splitlines():
                    line_str = line.strip()
                    if line_str in ("{", "}", "UPDATE", "HARVEST") or not line_str:
                        continue
                    formatted = line_str if (line_str.startswith(";") or line_str.endswith(":") or line_str.startswith("    ")) else f"    {line_str}"
                    lines.append(formatted)
            return lines

        update_lines  = extract_lines(clean_items[update_idx + 1:harvest_idx])
        harvest_lines = extract_lines(clean_items[harvest_idx + 2:])

        # HELPER: SITE-TAGGING VOOR DE 3 HARVEST EMISSIES
        def tag_harvest_lines(lines, tag):
            if not lines:
                return []
            
            local_labels = set()
            for line in lines:
                l_str = line.strip()
                if l_str.endswith(":") and not l_str.startswith(";"):
                    local_labels.add(l_str[:-1].strip())

            if not local_labels:
                return lines

            tagged_lines = []
            for line in lines:
                mod_line = line
                for lbl in local_labels:
                    mod_line = re.sub(rf'\b{re.escape(lbl)}\b', f"{lbl}_{tag}", mod_line)
                tagged_lines.append(mod_line)
            return tagged_lines

        harvest_early = tag_harvest_lines(harvest_lines, "EARLY")
        harvest_full  = tag_harvest_lines(harvest_lines, "FULL")
        harvest_drain = tag_harvest_lines(harvest_lines, "DRAIN")

        test_instr = ""
        if cond:
            if cond["op"] == "ZERO":
                test_instr = f"    TSTZ {cond['reg']}"
            elif cond["op"] == "==":
                test_instr = f"    TSTE {cond['arg1']}, {cond['arg2']}"
            elif cond["op"] == ">":
                test_instr = f"    TSTG {cond['arg1']}, {cond['arg2']}"

        jump_drain = f"    JMPT {lbl_drain}" if if_mode == "TRUE" else f"    JMPF {lbl_drain}"

        asm = [f"; --- START GEGENEREERDE SPAWN PIJPLIJN (ID: {spawn_id}) ---"]

        # 1. HOOFDLUS (Evalueer stopconditie & Vuur CONTEXT af)
        asm.append(f"{lbl_loop}:")
        if test_instr:
            asm.append(test_instr)
        asm.append(jump_drain)

        asm.append(f"    CONTEXT {input_reg}, {worker_label}")
        asm.append(f"    FAIL {lbl_full}")

        # UPDATE (Pas na geslaagde spawn!)
        for line in update_lines:
            asm.append(line)

        # 2. EARLY GREEDY HARVEST
        asm.append(f"    JOIN {harvest_reg}, {lbl_loop}")
        for line in harvest_early:
            asm.append(line)
        asm.append(f"    JMP {lbl_loop}")

        # 3. MATRIX FULL HANDLER
        asm.append(f"{lbl_full}:")
        asm.append(f"    JOIN {harvest_reg}, {lbl_full}")
        for line in harvest_full:
            asm.append(line)
        asm.append(f"    JMP {lbl_loop}")

        # 4. WATERDICHTE DRAIN FASE (Met correcte SYNC-loopback)
        asm.append(f"{lbl_drain}:")
        asm.append(f"    JOIN {harvest_reg}, {lbl_wait}")
        for line in harvest_drain:
            asm.append(line)
        asm.append(f"{lbl_wait}:")
        asm.append(f"    SYNC {lbl_drain}")
        asm.append(f"{lbl_done}:")
        asm.append(f"; --- EINDE GEGENEREERDE SPAWN PIJPLIJN ---")

        return "\n".join(asm)







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

    def if_condition(self, items):
        """
        Zet de conditie-node uit de grammatica om naar een schoon dictionary object.
        """
        clean = [str(x).strip() for x in items if x is not None]
        if "ZERO" in clean or (len(clean) >= 2 and clean[1] == "ZERO"):
            return {"op": "ZERO", "reg": clean[0]}
        elif "==" in clean:
            return {"op": "==", "arg1": clean[0], "arg2": clean[2]}
        elif ">" in clean:
            return {"op": ">", "arg1": clean[0], "arg2": clean[2]}
        return {"op": "UNKNOWN", "tokens": clean}

    def if_stmt(self, items):
        if_id = self.loop_counter
        self.loop_counter += 1

        else_label = f"__IF_ELSE_{if_id}"
        endif_label = f"__IF_END_{if_id}"

        cond = None
        mode = "TRUE"
        has_else = False
        if_body_lines = []
        else_body_lines = []
        in_else = False

        # 1. Doorloop de items en ontleed de conditie, modus en body-regels
        for item in items:
            if item is None:
                continue

            # Als if_condition al is omgezet naar een dict:
            if isinstance(item, dict) and "op" in item:
                cond = item
                continue

            # Fallback als item nog een onbewerkte Lark Tree is:
            if hasattr(item, 'data') and ('condition' in str(item.data) or item.data == 'if_condition'):
                children = [str(c).strip() for c in item.children]
                if "ZERO" in children or (len(children) >= 2 and children[1] == "ZERO"):
                    cond = {"op": "ZERO", "reg": children[0]}
                elif "==" in children:
                    cond = {"op": "==", "arg1": children[0], "arg2": children[2]}
                elif ">" in children:
                    cond = {"op": ">", "arg1": children[0], "arg2": children[2]}
                continue

            item_str = str(item).strip()

            if item_str in ("TRUE", "FALSE"):
                mode = item_str
                continue

            if item_str == "ELSE":
                has_else = True
                in_else = True
                continue

            if item_str in ("IF", "{", "}", "(", ")") or not item_str:
                continue

            # Verwerk instructieregels binnen het blok
            lines = [line.strip() for line in str(item).splitlines() if line.strip()]
            for line in lines:
                if line in ("{", "}", "ELSE") or not line:
                    continue

                formatted = line if (line.startswith(";") or line.endswith(":") or line.startswith("    ")) else f"    {line}"

                if in_else:
                    else_body_lines.append(formatted)
                else:
                    if_body_lines.append(formatted)

        # 2. Bouw de STERN Assembly-output op
        asm = [f"; --- IF STATEMENT START (ID: {if_id}) ---"]

        # Genereer gegarandeerd de test-instructie vόόr de sprong!
        if cond:
            if cond["op"] == "ZERO":
                asm.append(f"    TSTZ {cond['reg']}")
            elif cond["op"] == "==":
                asm.append(f"    TSTE {cond['arg1']}, {cond['arg2']}")
            elif cond["op"] == ">":
                asm.append(f"    TSTG {cond['arg1']}, {cond['arg2']}")

        target_label = else_label if has_else else endif_label

        if mode == "TRUE":
            asm.append(f"    JMPF {target_label}")
        else:
            asm.append(f"    JMPT {target_label}")

        for line in if_body_lines:
            asm.append(line)

        if has_else:
            asm.append(f"    JMP {endif_label}")
            asm.append(f"{else_label}:")
            for line in else_body_lines:
                asm.append(line)

        asm.append(f"{endif_label}:")
        asm.append(f"; --- IF STATEMENT END ---")

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