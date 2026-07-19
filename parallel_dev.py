# De Syntax

# PARALLEL (XOR_WORKER) USING [INbuffer + X] UNTIL (A == B) {
#     INTO [ENCODEbuffer + Y]
# }

# De grammer

grammar = """
start: _NL? map_block _NL? program_block _NL?

map_block: "MAP" _NL? "{" (_NL | map_directive)* "}"
?map_directive: start_stmt | res_stmt | const_stmt | io_stmt | memsize_stmt | sp_stmt | macro_def

memsize_stmt: "MEMSIZE" INT
sp_stmt:      "SP" INT
start_stmt:   "START" IDENTIFIER
res_stmt:     "RES" IDENTIFIER INT
const_stmt:   "CONST" IDENTIFIER INT
io_stmt:      "IO" IDENTIFIER INT

macro_def:  "MACRO" IDENTIFIER "(" [param_list] ")" "{" (_NL | program_line)* "}"
param_list: IDENTIFIER ("," IDENTIFIER)*

program_block: "PROGRAM" "{" (_NL | program_line)* "}"

# Gecorrigeerd: parallel_stmt is nu een geldige program_line
?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt | parallel_stmt) _NL

assignment: assign_source "->" assign_target
?assign_source: REGISTER | INT | IDENTIFIER | mem_ref
?assign_target: REGISTER | mem_ref

mem_ref: "[" (IDENTIFIER | INT) "]"
       | "[" (IDENTIFIER | INT) "+" REGISTER "]"

repeat_stmt: REPEAT_KEYWORD repeat_tail _NL? "{" (_NL | program_line)* "}"
repeat_tail: REGISTER TIMES_KEYWORD (INT | IDENTIFIER)
            | UNTIL_KEYWORD "(" argument COMPARATOR argument ")"
            | REGISTER TIMES_KEYWORD (INT | IDENTIFIER) UNTIL_KEYWORD "(" argument COMPARATOR argument ")"

# --- PARALLEL SYNTAX MET KRACHTIGE KEYWORDS ---
parallel_stmt: PARALLEL_KEYWORD "(" IDENTIFIER ")" USING_KEYWORD mem_ref UNTIL_KEYWORD "(" argument COMPARATOR argument ")" "{" _NL? INTO_KEYWORD mem_ref _NL? "}"

# Vaste tokens met hoge prioriteit om lexer-clashes te voorkomen
REPEAT_KEYWORD.2: "REPEAT"
TIMES_KEYWORD.2:  "TIMES"
UNTIL_KEYWORD.2:  "UNTIL"
PARALLEL_KEYWORD.2: "PARALLEL"
USING_KEYWORD.2:  "USING"
INTO_KEYWORD.2:   "INTO"
            
label_def: IDENTIFIER ":"
instruction: MNEMONIC [argument (","? argument)*]
?argument: REGISTER | IDENTIFIER | INT

macro_call: IDENTIFIER ["(" [arg_list] ")"]
arg_list:   argument (","? argument)*

MNEMONIC.2: /\\b(LDI|CONTEXT|OUT|IN|HALT|JMP|INC|DEC|RETURN|STO|STX|LDX|LDM|MUL|JOIN|CLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC)\\b/
REGISTER.2: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/
COMPARATOR.2: "==" | ">"
IDENTIFIER.1: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

%import common.INT
%import common.NEWLINE
_NL: NEWLINE
COMMENT: ";" /[^\\r\\n]*/
%ignore COMMENT
WS_INLINE: /[ \\t]+/
%ignore WS_INLINE
"""

# De executie

def parallel_stmt(self, items):
        """
        Genereert een hygiënische hardware-parallel loop die optimaal gebruik maakt 
        van de 32 cores, high-watermark context spawns en asynchrone JOIN/SYNC constructies.
        """
        worker_name = str(items[0])
        src_mem = str(items[1])
        arg1 = str(items[2])
        comparator = str(items[3])
        arg2 = str(items[4])
        dest_mem = str(items[5])

        # Interne helper om geheugen operand te ontleden naar (base, index)
        def parse_memory_operand(operand):
            inner = operand.strip("[] ")
            if '+' in inner:
                parts = inner.split('+')
                return parts[0].strip(), parts[1].strip()
            return inner, None

        src_base, src_idx = parse_memory_operand(src_mem)
        dest_base, dest_idx = parse_memory_operand(dest_mem)

        # Genereer unieke labels om clashes te voorkomen
        pipe_id = self.loop_counter
        self.loop_counter += 1

        lbl_loop    = f"__PIPE_{pipe_id}_LOOP"
        lbl_harvest = f"__PIPE_{pipe_id}_HARVEST"
        lbl_drain   = f"__PIPE_{pipe_id}_DRAIN"
        lbl_collect = f"__PIPE_{pipe_id}_COLLECT"
        lbl_done    = f"__PIPE_{pipe_id}_DONE"

        asm = [f"; --- START GEGENEREERDE HARDWARE PARALLEL (ID: {pipe_id}) ---"]

        # --- 1. DE HOOFDLUS: DATA INLADEN & CONDITIE CHECK ---
        asm.append(f"{lbl_loop}:")
        if src_idx:
            if src_idx != 'I':
                asm.append(f"    LD I, {src_idx}")
            asm.append(f"    LDX A, {src_base}")
        else:
            asm.append(f"    LDM A, {src_base}")

        # Evalueer de UNTIL stop-conditie (bijv. A == B)
        if comparator == "==":
            asm.append(f"    TSTE {arg1}, {arg2}")
        elif comparator == ">":
            asm.append(f"    TSTG {arg1}, {arg2}")
        asm.append(f"    JMPT {lbl_drain}")

        # --- 2. HARDWARE THREAD SPAWNEN ---
        asm.append(f"    CONTEXT A, {worker_name}")
        asm.append(f"    FAIL {lbl_harvest}")  # Matrix vol (< 10 cores vrij)? Oogst eerst de oudste thread!
        
        # Succesvol gespawnd: schuif de invoerpointer op en vul de matrix verder
        if src_idx:
            asm.append(f"    INC {src_idx}")
        asm.append(f"    JMP {lbl_loop}")

        # --- 3. TUSSENTIJDS OOGSTEN (Als de core matrix vol raakt) ---
        asm.append(f"{lbl_harvest}:")
        asm.append(f"    JOIN A, {lbl_harvest}")
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX A, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO A, {dest_base}")
        asm.append(f"    JMP {lbl_loop}")

        # --- 4. LEEGDRAAI-FASE (Conditie is bereikt, invoer gestopt) ---
        asm.append(f"{lbl_drain}:")
        # SYNC springt naar het label als er nog actieve contexts draaien, anders fallthrough
        asm.append(f"    SYNC {lbl_collect}")
        asm.append(f"    JMP {lbl_done}")

        asm.append(f"{lbl_collect}:")
        asm.append(f"    JOIN A, {lbl_collect}")
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX A, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO A, {dest_base}")
        asm.append(f"    JMP {lbl_drain}")

        # --- 5. AFSLUITING (Matrix is leeg, schrijf eventueel het eindkarakter weg) ---
        asm.append(f"{lbl_done}:")
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LD I, {dest_idx}")
            asm.append(f"    STX {arg2}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {arg2}, {dest_base}")

        asm.append(f"; --- EINDE GEGENEREERDE HARDWARE PARALLEL ---")
        return "\n".join(asm)