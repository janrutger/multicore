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

?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt | if_stmt | spawn_stmt) _NL

assignment: assign_source "->" assign_target
?assign_source: REGISTER | INT | IDENTIFIER | mem_ref
?assign_target: REGISTER | mem_ref

mem_ref: "[" (IDENTIFIER | INT) "]"
       | "[" (IDENTIFIER | INT) "+" REGISTER "]"

if_stmt: IF_KEYWORD "(" if_condition ")" IF_MODE _NL? "{" (_NL | program_line)* "}" [ ELSE_KEYWORD _NL? "{" (_NL | program_line)* "}" ]
?if_condition: REGISTER ZERO_KEYWORD
             | argument COMPARATOR argument

IF_KEYWORD.2:   "IF"
ELSE_KEYWORD.2: "ELSE"
IF_MODE.2:      "TRUE" | "FALSE"
ZERO_KEYWORD.2: "ZERO"

spawn_stmt: SPAWN_KEYWORD IDENTIFIER REGISTER UNTIL_KEYWORD "(" if_condition ")" IF_MODE UPDATE_KEYWORD _NL? "{" (_NL | program_line)* "}" HARVEST_KEYWORD REGISTER _NL? "{" (_NL | program_line)* "}"

SPAWN_KEYWORD.2:   "SPAWN"
UPDATE_KEYWORD.2:  "UPDATE"
HARVEST_KEYWORD.2: "HARVEST"

repeat_stmt: REPEAT_KEYWORD repeat_tail _NL? "{" (_NL | program_line)* "}"
repeat_tail: REGISTER TIMES_KEYWORD (INT | IDENTIFIER)
            | UNTIL_KEYWORD "(" argument COMPARATOR argument ")"
            | REGISTER TIMES_KEYWORD (INT | IDENTIFIER) UNTIL_KEYWORD "(" argument COMPARATOR argument ")"

REPEAT_KEYWORD.2: "REPEAT"
TIMES_KEYWORD.2:  "TIMES"
UNTIL_KEYWORD.2:  "UNTIL"
            
label_def: IDENTIFIER ":"
instruction: MNEMONIC [argument (","? argument)*]
?argument: REGISTER | IDENTIFIER | INT

macro_call: IDENTIFIER ["(" [arg_list] ")"]
arg_list:   argument (","? argument)*

MNEMONIC.2: /\\b(LDI|CONTEXT|RCONTEXT|ALLSYNC|BOOT_REMOTE|OUT|IN|HALT|JMP|INC|DEC|STO|STX|LDX|LDM|LD|MUL|JOIN|CLOSE|AUTOCLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC|SM32_RND|SHIFTR|SHIFTL|ADDI|SUBI|MULI|DIV|DIVI)\\b/
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

# map_block: "MAP" _NL? "{" (_NL | map_directive)* "}"
# ?map_directive: start_stmt | res_stmt | const_stmt | io_stmt | memsize_stmt | sp_stmt | macro_def

# memsize_stmt: "MEMSIZE" INT
# sp_stmt:      "SP" INT
# start_stmt:   "START" IDENTIFIER
# res_stmt:     "RES" IDENTIFIER INT
# const_stmt:   "CONST" IDENTIFIER INT
# io_stmt:      "IO" IDENTIFIER INT

# macro_def:  "MACRO" IDENTIFIER "(" [param_list] ")" "{" (_NL | program_line)* "}"
# param_list: IDENTIFIER ("," IDENTIFIER)*

# program_block: "PROGRAM" "{" (_NL | program_line)* "}"

# # ?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt) _NL
# ?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt | if_stmt) _NL


# assignment: assign_source "->" assign_target
# ?assign_source: REGISTER | INT | IDENTIFIER | mem_ref
# ?assign_target: REGISTER | mem_ref

# mem_ref: "[" (IDENTIFIER | INT) "]"
#        | "[" (IDENTIFIER | INT) "+" REGISTER "]"


# # if_stmt: IF_KEYWORD "(" if_condition ")" IF_MODE      "{" (_NL | program_line)* "}" [ ELSE_KEYWORD      "{" (_NL | program_line)* "}" ]
# if_stmt: IF_KEYWORD "(" if_condition ")" IF_MODE _NL? "{" (_NL | program_line)* "}" [ ELSE_KEYWORD _NL? "{" (_NL | program_line)* "}" ]

# ?if_condition: REGISTER ZERO_KEYWORD
#              | argument COMPARATOR argument

# IF_KEYWORD.2:   "IF"
# ELSE_KEYWORD.2: "ELSE"
# IF_MODE.2:      "TRUE" | "FALSE"
# ZERO_KEYWORD.2: "ZERO"

# repeat_stmt: REPEAT_KEYWORD repeat_tail _NL? "{" (_NL | program_line)* "}"
# repeat_tail: REGISTER TIMES_KEYWORD (INT | IDENTIFIER)
#             | UNTIL_KEYWORD "(" argument COMPARATOR argument ")"
#             | REGISTER TIMES_KEYWORD (INT | IDENTIFIER) UNTIL_KEYWORD "(" argument COMPARATOR argument ")"


# # Vaste tokens met hoge prioriteit om lexer-clashes te voorkomen
# REPEAT_KEYWORD.2: "REPEAT"
# TIMES_KEYWORD.2:  "TIMES"
# UNTIL_KEYWORD.2:  "UNTIL"
            
# label_def: IDENTIFIER ":"
# instruction: MNEMONIC [argument (","? argument)*]
# ?argument: REGISTER | IDENTIFIER | INT

# macro_call: IDENTIFIER ["(" [arg_list] ")"]
# arg_list:   argument (","? argument)*

# MNEMONIC.2: /\\b(LDI|CONTEXT|OUT|IN|HALT|JMP|INC|DEC|STO|STX|LDX|LDM|LD|MUL|JOIN|CLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC|SM32_RND)\\b/
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











