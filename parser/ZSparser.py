from lark import Lark, Transformer
from grammer import grammar
from assemblerV3 import assemble

class MacroExpander(Transformer):
    def __init__(self):
        super().__init__()
        self.macro_table = {}
        # Nieuw: een tabel om constanten, IO-poorten en RES-labels in op te slaan
        self.symbol_table = {}

    # --- NIEUW: Vang de MAP directives op en sla de waarden op ---
    def io_stmt(self, items):
        name = str(items[0])
        value = int(items[1]) # Direct naar int voor berekeningen
        self.symbol_table[name] = {"type": "IO", "value": value}
        return None

    def const_stmt(self, items):
        name = str(items[0])
        value = int(items[1])
        self.symbol_table[name] = {"type": "CONST", "value": value}
        return None

    def res_stmt(self, items):
        name = str(items[0])
        value = int(items[1]) # Aantal gereserveerde bytes/woorden
        self.symbol_table[name] = {"type": "RES", "value": value}
        return None

    def start_stmt(self, items):
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
            return f"{mnemonic} {', '.join(args)}"
        return f"{mnemonic}"

    def label_def(self, items):
        return f"{items[0]}:"

    def macro_call(self, items):
        macro_name = str(items[0])
        args = items[1] if len(items) > 1 else []

        if macro_name not in self.macro_table:
            raise NameError(f"Fout: Macro '{macro_name}' is niet gedefinieerd!")

        macro = self.macro_table[macro_name]
        
        if len(args) != len(macro["params"]):
            raise ValueError(f"Fout: {macro_name} verwacht {len(macro['params'])} args, kreeg {len(args)}.")

        param_map = dict(zip(macro["params"], args))
        expanded_lines = [f"; --- Start macro: {macro_name} ---"]

        for instr in macro["body"]:
            tokens = instr.replace(',', ' ').split()
            if not tokens:
                continue
            mnemonic = tokens[0]
            replaced_args = [param_map.get(tok, tok) for tok in tokens[1:]]
            
            if replaced_args:
                expanded_lines.append(f"    {mnemonic} {', '.join(replaced_args)}")
            else:
                expanded_lines.append(f"    {mnemonic}")
            
        expanded_lines.append(f"; --- Einde macro: {macro_name} ---")
        return "\n".join(expanded_lines)

    def arg_list(self, items):
        return [str(i) for i in items]

    def map_block(self, items):
        # We hoeven het MAP-blok zelf niet terug te zien in de pure assembly output
        return None

    def program_block(self, items):
        lines = [str(item) for item in items if item and str(item) != 'None']
        return "\n".join(lines)

    def start(self, items):
        program_code = items[1]
        
        # --- DE FINALE PAS: Vervang alle bekende constanten/IO-labels door hun waarde ---
        for symbol, info in self.symbol_table.items():
            actual_value = str(info["value"])
            
            import re
            program_code = re.sub(rf'\b{symbol}\b', actual_value, program_code)
            
        return program_code
            

# --- TEST MET JOUW INPUT ---
# source_code = """
# MAP {
#     START   main
#     IO      X_value   2
    
#     MACRO SET_AND_OUT(reg, waarde, poort) {
#         LDI reg, waarde
#         OUT reg, poort
#     }
# }

# PROGRAM {
#     main:
#         SET_AND_OUT(A, 10, X_value)
#         LDI A 10
#         HALT
# }
# """

source_code = """
MAP {
    START   main
    IO      X_value   2
    MACRO SET_AND_OUT(reg, waarde, poort) {
        LDI reg, waarde
        OUT reg, poort
    }
}

PROGRAM {
; ==========================================================
;  15x CONTEXT STRESSTEST (Gecorrigeerd)
; ==========================================================
    LDI A 5             ; Bronwaarde voor de threads (blijft ALTIJD 1)
    LDI I 0             ; Lus-teller I = 0
    LDI Y 150            ; De doelwaarde (15 iteraties)
    LDI X 0             ; Totaalteller X = 0

SPAWN_LOOP:
    TSTE I Y            
    JMPT FLUSH_REMAINING 

    CONTEXT A THREAD_WORKER 
    FAIL MATRIX_FULL_HANDLER  

    INC I   

    JOIN B SPAWN_LOOP
    ADD X B

    JMP SPAWN_LOOP      

MATRIX_FULL_HANDLER:
    ; Oogst in register B in plaats van A! Hierdoor blijft Master-register A intact.
    JOIN B MATRIX_FULL_HANDLER 
    
    ADD X B             ; Tel het resultaat uit B op bij het totaal X

    JMP SPAWN_LOOP

; ==========================================================
;  FINALE FLUSH
; ==========================================================
FLUSH_REMAINING:
    ; Oogst ook hier in register B!
    JOIN B ALL_DONE     

    ADD X B
    JMP FLUSH_REMAINING

ALL_DONE:

    SYNC FLUSH_REMAINING

    STO X 512           ; Sla het eindresultaat op op adres 512
    HALT                

; ==========================================================
;  PARALLELLE WORKER THREAD CODE
; ==========================================================
THREAD_WORKER: 
    LDI M 42
    LDI L 42
    MUL M L

    LDI B 1             
    MUL B A  

    RETURN B
    ;CLOSE
}
"""



# parser = Lark(grammar, parser='lalr')
# parse_tree = parser.parse(source_code)
# expander = MacroExpander()
# schone_assembly = expander.transform(parse_tree)

# print("--- Output ---") 
# print(schone_assembly)

# print(assemble(schone_assembly))



