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

MNEMONIC.2: /\\b(LDI|CONTEXT|OUT|IN|HALT|JMP|INC|DEC|RETURN|STO|STX|LDX|LDM|LD|MUL|JOIN|CLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC|SM32_RND)\\b/
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



# grammar = """
# start: _NL? map_block _NL? program_block _NL?

# // We staan nu toe dat het map_block bestaat uit een willekeurige mix van map_directives en losse newlines (_NL)
# map_block: "MAP" _NL? "{" (_NL | map_directive)* "}"

# ?map_directive: start_stmt | res_stmt | const_stmt | io_stmt | memsize_stmt | sp_stmt | macro_def

# memsize_stmt: "MEMSIZE" INT
# sp_stmt:      "SP" INT
# start_stmt:   "START" IDENTIFIER
# res_stmt:     "RES" IDENTIFIER INT
# const_stmt:   "CONST" IDENTIFIER INT
# io_stmt:      "IO" IDENTIFIER INT

# // FIX: Macro's staan nu ook interne labels en herhalingen toe (net als het program_block)
# macro_def:  "MACRO" IDENTIFIER "(" [param_list] ")" "{" (_NL | program_line)* "}"
# param_list: IDENTIFIER ("," IDENTIFIER)*

# // We staan nu toe dat het program_block bestaat uit een willekeurige mix van program_lines en losse newlines (_NL)
# program_block: "PROGRAM" "{" (_NL | program_line)* "}"

# // Een echte regel is nu ofwel een label, of een instructie/macro/repeat die eindigt met een newline
# // Voeg 'assignment' toe aan de geldige regels:
# ?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt) _NL



# // De toewijzingsregel
# assignment: assign_source "->" assign_target

# // Definieer wat links en rechts mag staan
# ?assign_source: REGISTER | INT | IDENTIFIER | mem_ref
# ?assign_target: REGISTER | mem_ref

# // Geheugen-referenties: [adres], [512], [adres + Ry], of [512 + Ry]
# mem_ref: "[" (IDENTIFIER | INT) "]"
#        | "[" (IDENTIFIER | INT) "+" REGISTER "]"



# // --- REPEAT DEFINITIES ---
# repeat_stmt: REPEAT_KEYWORD repeat_tail _NL? "{" (_NL | program_line)* "}"

# repeat_tail: REGISTER TIMES_KEYWORD (INT | IDENTIFIER)
#             | UNTIL_KEYWORD "(" argument COMPARATOR argument ")"
#             | REGISTER TIMES_KEYWORD (INT | IDENTIFIER) UNTIL_KEYWORD "(" argument COMPARATOR argument ")"

# REPEAT_KEYWORD.2: "REPEAT"
# TIMES_KEYWORD.2:  "TIMES"
# UNTIL_KEYWORD.2:  "UNTIL"
            
# label_def: IDENTIFIER ":"

# instruction: MNEMONIC [argument (","? argument)*]
# ?argument: REGISTER | IDENTIFIER | INT

# macro_call: IDENTIFIER ["(" [arg_list] ")"]
# arg_list:   argument (","? argument)*

# MNEMONIC.2: /\\b(LDI|CONTEXT|OUT|IN|HALT|JMP|INC|DEC|RETURN|STO|STX|MUL|JOIN|CLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC)\\b/
# REGISTER.2: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/

# COMPARATOR.2: "==" | ">"
# IDENTIFIER.1: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

# %import common.INT
# %import common.NEWLINE

# _NL: NEWLINE
# COMMENT: ";" /[^\\r\\n]*/
# %ignore COMMENT

# WS_INLINE: /[ \\t]+/
# %ignore WS_INLINE
# """


