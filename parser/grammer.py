# grammar = """
# start: map_block program_block

# map_block: "MAP" "{" map_directive* "}"
# ?map_directive: start_stmt | res_stmt | const_stmt | io_stmt | macro_def

# start_stmt: "START" IDENTIFIER
# res_stmt:   "RES" IDENTIFIER INT
# const_stmt: "CONST" IDENTIFIER INT
# io_stmt:    "IO" IDENTIFIER INT

# macro_def:  "MACRO" IDENTIFIER "(" [param_list] ")" "{" instruction+ "}"
# param_list: IDENTIFIER ("," IDENTIFIER)*

# program_block: "PROGRAM" "{" program_line* "}"
# ?program_line: label_def | instruction | macro_call

# label_def: IDENTIFIER ":"

# // De parser-regel is nu weer lekker clean: een instructie begint ALTIJD met een MNEMONIC
# instruction: MNEMONIC [argument (","? argument)*]
# ?argument: REGISTER | IDENTIFIER | INT

# macro_call: IDENTIFIER "(" [arg_list] ")"
# arg_list:   argument ("," argument)*

# // DE GOUDEN COMBINATIE: Regex + Word Boundaries + Hoge Prioriteit (.10)
# MNEMONIC.10: /\\b(LDI|CONTEXT|OUT|IN|HALT|JMP|INC|DEC|RETURN)\\b/
# REGISTER.10: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/

# // De algemene identifier voor variabelen/labels
# IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

# %import common.INT
# %import common.WS

# // Negeer alles vanaf een puntkomma tot het einde van de regel
# COMMENT: ";" /[^\\r\\n]*/
# %ignore COMMENT
# %ignore WS
# """

grammar = """
start: _NL? map_block _NL? program_block _NL?

map_block: "MAP" _NL? "{" _NL? map_directive* "}"
?map_directive: (start_stmt | res_stmt | const_stmt | io_stmt | macro_def) _NL

start_stmt: "START" IDENTIFIER
res_stmt:   "RES" IDENTIFIER INT
const_stmt: "CONST" IDENTIFIER INT
io_stmt:    "IO" IDENTIFIER INT

macro_def:  "MACRO" IDENTIFIER "(" [param_list] ")" "{" _NL? (instruction _NL)+ "}"
param_list: IDENTIFIER ("," IDENTIFIER)*

// We staan nu toe dat het program_block bestaat uit een willekeurige mix van program_lines en losse newlines (_NL)
program_block: "PROGRAM" "{" (_NL | program_line)* "}"

// Een echte regel is nu ofwel een label, of een instructie/macro die eindigt met een newline
?program_line: label_def _NL? | (instruction | macro_call) _NL

label_def: IDENTIFIER ":"

// Instructie met flexibele argumenten
instruction: MNEMONIC [argument (","? argument)*]
?argument: REGISTER | IDENTIFIER | INT

macro_call: IDENTIFIER "(" [arg_list] ")"
arg_list:   argument ("," argument)*

// De ondersteunde mnemonics en registers
MNEMONIC.10: /\\b(LDI|CONTEXT|OUT|IN|HALT|JMP|INC|DEC|RETURN|STO|MUL|JOIN|CLOSE)\\b/
REGISTER.10: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/

IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

%import common.INT
%import common.NEWLINE

// We gebruiken de ingebouwde NEWLINE van Lark als onze _NL
_NL: NEWLINE

// COMMENT blijft super simpel en veilig: eet alles op tot de newline, maar laat de newline zelf met rust
COMMENT: ";" /[^\\r\\n]*/
%ignore COMMENT

// We negeren alleen inline whitespaces (spaties en tabs)
WS_INLINE: /[ \\t]+/
%ignore WS_INLINE
"""