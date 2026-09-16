grammar = """
start: _NL* map_block _NL* program_block _NL*

map_block: _MAP_KW _NL? "{" (_NL | map_directive)* "}"
?map_directive: start_stmt | res_stmt | sres_stmt | pres_stmt | const_stmt | io_stmt | memsize_stmt | sp_stmt | memory_block | macro_def

_MEMSIZE_KW.2: "MEMSIZE"
_SP_KW.2:      "SP"
_START_KW.2:   "START"
_RES_KW.2:     "RES"
_CONST_KW.2:   "CONST"
_IO_KW.2:      "IO"
_MAP_KW.2:     "MAP"
_MACRO_KW.2:   "MACRO"

memsize_stmt: _MEMSIZE_KW INT
sp_stmt:      _SP_KW INT
start_stmt:   _START_KW IDENTIFIER
res_stmt:     _RES_KW IDENTIFIER INT
const_stmt:   _CONST_KW IDENTIFIER INT
io_stmt:      _IO_KW IDENTIFIER INT

// === MEMORY GEHEUGENMAP BLOK & DECLARATIES ===
_MEMORY_KW.2:  "MEMORY"
_PROGRAM_KW.2: "PROGRAM"
_SHARED_KW.2:  "SHARED"
_PRIVATE_KW.2: "PRIVATE"

memory_block: _MEMORY_KW _NL? "{" (_NL | memory_stmt)* "}"
?memory_stmt: program_size_stmt | shared_size_stmt | private_size_stmt
program_size_stmt: _PROGRAM_KW INT
shared_size_stmt:  _SHARED_KW INT
private_size_stmt: _PRIVATE_KW INT

// SHARED en PRIVATE als reserverings-instructies (Categorie 1)
sres_stmt: _SHARED_KW IDENTIFIER INT
pres_stmt: _PRIVATE_KW IDENTIFIER INT

macro_def:  _MACRO_KW IDENTIFIER "(" [param_list] ")" "{" (_NL | program_line)* "}"
param_list: IDENTIFIER ("," IDENTIFIER)*

program_block: _PROGRAM_KW "{" (_NL | program_line)* "}"

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

MNEMONIC.2: /\\b(LDI|CONTEXT|RCONTEXT|ALLSYNC|BOOT_REMOTE|RBOOT|OUT|IN|HALT|JMP|INC|DEC|STO|STX|LDX|LDM|LD|MUL|JOIN|CLOSE|AUTOCLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC|SM32_RND|SHIFTR|SHIFTL|ADDI|SUBI|MULI|DIV|DIVI)\\b/
REGISTER.2: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/
COMPARATOR.2: "==" | "!=" | ">" | "<"
IDENTIFIER.1: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

%import common.SIGNED_INT -> INT
%import common.NEWLINE
_NL: NEWLINE
COMMENT: ";" /[^\\r\\n]*/
%ignore COMMENT
WS_INLINE: /[ \\t]+/
%ignore WS_INLINE
"""


# grammar = """
# start: _NL* map_block _NL* program_block _NL*

# map_block: _MAP_KW _NL? "{" (_NL | map_directive)* "}"
# ?map_directive: start_stmt | res_stmt | sres_stmt | pres_stmt | const_stmt | io_stmt | memsize_stmt | sp_stmt | memory_block | macro_def

# _MEMSIZE_KW.2: "MEMSIZE"
# _SP_KW.2:      "SP"
# _START_KW.2:   "START"
# _RES_KW.2:     "RES"
# _SRES_KW.2:    "SRES"
# _PRES_KW.2:    "PRES"
# _CONST_KW.2:   "CONST"
# _IO_KW.2:      "IO"
# _MAP_KW.2:     "MAP"
# _MACRO_KW.2:   "MACRO"

# memsize_stmt: _MEMSIZE_KW INT
# sp_stmt:      _SP_KW INT
# start_stmt:   _START_KW IDENTIFIER
# res_stmt:     _RES_KW IDENTIFIER INT
# sres_stmt:    _SRES_KW IDENTIFIER INT
# pres_stmt:    _PRES_KW IDENTIFIER INT
# const_stmt:   _CONST_KW IDENTIFIER INT
# io_stmt:      _IO_KW IDENTIFIER INT

# // === NIEUW: MEMORY GEHEUGENMAP BLOK ===
# _MEMORY_KW.2:  "MEMORY"
# _PROGRAM_KW.2: "PROGRAM"
# _SHARED_KW.2:  "SHARED"
# _PRIVATE_KW.2: "PRIVATE"

# memory_block: _MEMORY_KW _NL? "{" (_NL | memory_stmt)* "}"
# ?memory_stmt: program_size_stmt | shared_size_stmt | private_size_stmt
# program_size_stmt: _PROGRAM_KW INT
# shared_size_stmt:  _SHARED_KW INT
# private_size_stmt: _PRIVATE_KW INT

# macro_def:  _MACRO_KW IDENTIFIER "(" [param_list] ")" "{" (_NL | program_line)* "}"
# param_list: IDENTIFIER ("," IDENTIFIER)*

# program_block: _PROGRAM_KW "{" (_NL | program_line)* "}"

# ?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt | if_stmt | spawn_stmt) _NL

# assignment: assign_source "->" assign_target
# ?assign_source: REGISTER | INT | IDENTIFIER | mem_ref
# ?assign_target: REGISTER | mem_ref

# mem_ref: "[" (IDENTIFIER | INT) "]"
#        | "[" (IDENTIFIER | INT) "+" REGISTER "]"

# if_stmt: IF_KEYWORD "(" if_condition ")" IF_MODE _NL? "{" (_NL | program_line)* "}" [ ELSE_KEYWORD _NL? "{" (_NL | program_line)* "}" ]
# ?if_condition: REGISTER ZERO_KEYWORD
#              | argument COMPARATOR argument

# IF_KEYWORD.2:   "IF"
# ELSE_KEYWORD.2: "ELSE"
# IF_MODE.2:      "TRUE" | "FALSE"
# ZERO_KEYWORD.2: "ZERO"

# spawn_stmt: SPAWN_KEYWORD IDENTIFIER REGISTER UNTIL_KEYWORD "(" if_condition ")" IF_MODE UPDATE_KEYWORD _NL? "{" (_NL | program_line)* "}" HARVEST_KEYWORD REGISTER _NL? "{" (_NL | program_line)* "}"

# SPAWN_KEYWORD.2:   "SPAWN"
# UPDATE_KEYWORD.2:  "UPDATE"
# HARVEST_KEYWORD.2: "HARVEST"

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

# MNEMONIC.2: /\\b(LDI|CONTEXT|RCONTEXT|ALLSYNC|BOOT_REMOTE|RBOOT|OUT|IN|HALT|JMP|INC|DEC|STO|STX|LDX|LDM|LD|MUL|JOIN|CLOSE|AUTOCLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC|SM32_RND|SHIFTR|SHIFTL|ADDI|SUBI|MULI|DIV|DIVI)\\b/
# REGISTER.2: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/
# COMPARATOR.2: "==" | "!=" | ">" | "<"
# IDENTIFIER.1: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

# %import common.SIGNED_INT -> INT
# %import common.NEWLINE
# _NL: NEWLINE
# COMMENT: ";" /[^\\r\\n]*/
# %ignore COMMENT
# WS_INLINE: /[ \\t]+/
# %ignore WS_INLINE
# """



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

# ?program_line: label_def _NL? | (instruction | assignment | macro_call | repeat_stmt | if_stmt | spawn_stmt) _NL

# assignment: assign_source "->" assign_target
# ?assign_source: REGISTER | INT | IDENTIFIER | mem_ref
# ?assign_target: REGISTER | mem_ref

# mem_ref: "[" (IDENTIFIER | INT) "]"
#        | "[" (IDENTIFIER | INT) "+" REGISTER "]"

# if_stmt: IF_KEYWORD "(" if_condition ")" IF_MODE _NL? "{" (_NL | program_line)* "}" [ ELSE_KEYWORD _NL? "{" (_NL | program_line)* "}" ]
# ?if_condition: REGISTER ZERO_KEYWORD
#              | argument COMPARATOR argument

# IF_KEYWORD.2:   "IF"
# ELSE_KEYWORD.2: "ELSE"
# IF_MODE.2:      "TRUE" | "FALSE"
# ZERO_KEYWORD.2: "ZERO"

# spawn_stmt: SPAWN_KEYWORD IDENTIFIER REGISTER UNTIL_KEYWORD "(" if_condition ")" IF_MODE UPDATE_KEYWORD _NL? "{" (_NL | program_line)* "}" HARVEST_KEYWORD REGISTER _NL? "{" (_NL | program_line)* "}"

# SPAWN_KEYWORD.2:   "SPAWN"
# UPDATE_KEYWORD.2:  "UPDATE"
# HARVEST_KEYWORD.2: "HARVEST"

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

# MNEMONIC.2: /\\b(LDI|CONTEXT|RCONTEXT|ALLSYNC|BOOT_REMOTE|OUT|IN|HALT|JMP|INC|DEC|STO|STX|LDX|LDM|LD|MUL|JOIN|CLOSE|AUTOCLOSE|TSTE|FAIL|SUCCES|SYNC|ADD|SUB|MOD|TSTG|XOR|JMPT|JMPF|TSTZ|IOSYNC|SM32_RND|SHIFTR|SHIFTL|ADDI|SUBI|MULI|DIV|DIVI)\\b/
# REGISTER.2: /\\b(A|B|C|D|K|L|M|X|Y|Z|I)\\b/
# COMPARATOR.2: "==" | ">"
# IDENTIFIER.1: /[a-zA-Z_][a-zA-Z0-9_\\-]*/

# %import common.SIGNED_INT -> INT
# %import common.NEWLINE
# _NL: NEWLINE
# COMMENT: ";" /[^\\r\\n]*/
# %ignore COMMENT
# WS_INLINE: /[ \\t]+/
# %ignore WS_INLINE
# """




