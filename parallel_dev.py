# De Syntax

# PARALLEL (threatname) USING [INbuffer + Rx] UNTIL (Rz == Rq) {
#     A -> [ENCODEbuffer + Ry]
# }

# PARALLEL (XOR_WORKER) USING [INbuffer + X] UNTIL (A == B) {
#     A -> [ENCODEbuffer + Y]
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

# parallel_stmt is nu een geldige program_line
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

# --- NIEUWE PARALLEL SYNTAX MET DATAFLOW PIJL DRIVERS ---
parallel_stmt: PARALLEL_KEYWORD "(" IDENTIFIER ")" USING_KEYWORD mem_ref UNTIL_KEYWORD "(" argument COMPARATOR argument ")" "{" _NL? REGISTER "->" mem_ref _NL? "}"

# Vaste tokens met hoge prioriteit om lexer-clashes te voorkomen
REPEAT_KEYWORD.2: "REPEAT"
TIMES_KEYWORD.2:  "TIMES"
UNTIL_KEYWORD.2:  "UNTIL"
PARALLEL_KEYWORD.2: "PARALLEL"
USING_KEYWORD.2:  "USING"
            
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
        Genereert een hygiënische hardware-parallel loop met een Greedy JOIN voor de Z32 matrix.
        Werkt non-blocking via de asynchrone CONTEXT/JOIN architectuur.
        """
        worker_name = str(items[0])
        src_mem     = str(items[1]) # Bijv. "[INbuffer + X]"
        
        # De UNTIL conditie elementen
        rz_reg     = str(items[2])  # Het register dat getest wordt (bijv. A)
        comparator = str(items[3])  # "==" of ">"
        rq_val     = str(items[4])  # De stop-waarde of stop-register (bijv. B of 27)
        
        # De dataflow pijl binnen de haken: REGISTER -> mem_ref
        dest_reg   = str(items[5])  # Het register dat geoogst wordt via JOIN (bijv. A)
        dest_mem   = str(items[6])  # De uitvoerbestemming (bijv. "[ENCODEbuffer + Y]")

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
                asm.append(f"    LDI I, {src_idx}")
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
                asm.append(f"    LDI I, {dest_idx}")
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
                asm.append(f"    LDI I, {dest_idx}")
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
                asm.append(f"    LDI I, {dest_idx}")
            asm.append(f"    STX {dest_reg}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {dest_reg}, {dest_base}")
        asm.append(f"    JMP {lbl_drain}")

        # --- 5. AFSLUITING (Sluit de buffer netjes af met de stop-waarde) ---
        asm.append(f"{lbl_done}:")
        if dest_idx:
            if dest_idx != 'I':
                asm.append(f"    LDI I, {dest_idx}")
            asm.append(f"    STX {rq_val}, {dest_base}")
            asm.append(f"    INC {dest_idx}")
        else:
            asm.append(f"    STO {rq_val}, {dest_base}")

        asm.append(f"; --- EINDE GEGENEREERDE HARDWARE PARALLEL ---\n")
        return "\n".join(asm)