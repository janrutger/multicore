import re
import sys
from typing import List, Tuple, Optional

# --- LEXER CONFIGURATIE ---
TOKEN_TYPES = [
    ('NL',            r'[\n\r]+'),     # Newlines krijgen nu een eigen identiteit!
    ('SKIP',          r'[ \t]+'),      # Spaties en tabs worden nog steeds genegeerd
    ('COMMENT',       r'//.*'),       
    ('MAP_BLOCK',     r'\bMAP\b'),
    ('PROG_BLOCK',    r'\bPROGRAM\b'),
    ('KEYWORD',       r'\b(void|register|if|else|for|while)\b'),
    ('IDENTIFIER',    r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'),
    ('NUMBER',        r'\b\d+\b'),
    ('LBRACE',        r'\{'),
    ('RBRACE',        r'\}'),
    ('LPAREN',        r'\('),
    ('RPAREN',        r'\)'),
    ('OPERATOR',      r'[<=>+\-*/,;]'),
]

class Token:
    def __init__(self, type_: str, value: str, line: int):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, '{self.value}', Line:{self.line})"

def lex(source_code: str) -> List[Token]:
    tokens = []
    line_num = 1
    
    token_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_TYPES)
    
    for mo in re.finditer(token_regex, source_code):
        kind = mo.lastgroup
        value = mo.group(kind)
        
        # Hou het regelnummer accuraat bij
        line_num += value.count('\n')
        
        if kind == 'SKIP' or kind == 'COMMENT':
            continue
        else:
            tokens.append(Token(kind, value, line_num))
            
    return tokens

# --- PARSER / ORCHESTRATOR ARCHITECTUUR ---
class ASTNode: pass

class MapSectionNode(ASTNode):
    def __init__(self, definitions):
        self.definitions = definitions

class ProgramSectionNode(ASTNode):
    def __init__(self, functions):
        self.functions = functions

class FunctionNode(ASTNode):
    def __init__(self, name: str, body: List[ASTNode]):
        self.name = name
        self.body = body

class AsmBlockNode(ASTNode):
    def __init__(self, code: str):
        self.code = code

class OrchestratorParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected_type: str) -> Token:
        token = self.peek()
        if not token:
            raise SyntaxError(f"Onverwacht einde van bestand. Verwachtte: {expected_type}")
        if token.type != expected_type:
            raise SyntaxError(f"Lijn {token.line}: Verwachtte {expected_type}, kreeg {token.type} ('{token.value}')")
        self.pos += 1
        return token

    def skip_newlines(self):
        while self.peek() and self.peek().type == 'NL':
            self.pos += 1

    def parse(self) -> List[ASTNode]:
        ast = []
        while self.peek():
            self.skip_newlines() # Sla loze newlines tussen blokken over
            if not self.peek(): break
            
            token = self.peek()
            if token.type == 'MAP_BLOCK':
                ast.append(self.parse_map_section())
            elif token.type == 'PROG_BLOCK':
                ast.append(self.parse_program_section())
            else:
                raise SyntaxError(f"Lijn {token.line}: Alleen MAP of PROGRAM blokken toegestaan op top-level. Kreeg: {token.type} ({token.value})")
        return ast

    def parse_map_section(self) -> MapSectionNode:
        self.consume('MAP_BLOCK')
        self.consume('LBRACE')
        
        definitions = {}
        while self.peek() and self.peek().type != 'RBRACE':
            self.skip_newlines()  # Sla newlines over aan het begin van de regel
            if not self.peek() or self.peek().type == 'RBRACE': break
            
            def_type = self.consume('IDENTIFIER').value 
            name = self.consume('IDENTIFIER').value
            
            value = None
            if self.peek() and self.peek().type == 'NUMBER':
                value = int(self.consume('NUMBER').value)
                
            definitions[name] = {'type': def_type, 'value': value}
            self.skip_newlines()  # Sla newlines over aan het einde van de regel
            
        self.consume('RBRACE')
        return MapSectionNode(definitions)

    def parse_program_section(self) -> ProgramSectionNode:
        self.consume('PROG_BLOCK')
        self.consume('LBRACE')
        
        functions = []
        while self.peek() and self.peek().type != 'RBRACE':
            self.skip_newlines()  # Sla loze newlines voor een functie over
            if not self.peek() or self.peek().type == 'RBRACE': break
            
            functions.append(self.parse_function())
            self.skip_newlines()  # Sla loze newlines na een functie over
            
        self.consume('RBRACE')
        return ProgramSectionNode(functions)

    def parse_function(self) -> FunctionNode:
        self.consume('KEYWORD')  # void
        func_name = self.consume('IDENTIFIER').value
        self.consume('LPAREN')
        self.consume('RPAREN')
        self.skip_newlines()
        self.consume('LBRACE')
        self.skip_newlines()
        
        body = []
        while self.peek() and self.peek().type != 'RBRACE':
            self.skip_newlines()
            token = self.peek()
            if not token or token.type == 'RBRACE': break
            
            if token.type == 'LBRACE':
                self.consume('LBRACE')
                asm_lines = []
                current_line = []
                brace_count = 1
                
                while brace_count > 0 and self.peek():
                    t = self.peek()
                    if t.type == 'LBRACE':
                        brace_count += 1
                    elif t.type == 'RBRACE':
                        brace_count -= 1
                        
                    if brace_count > 0:
                        if t.type == 'NL':
                            # Einde van de regel bereikt binnen het ASM-blok
                            if current_line:
                                asm_lines.append(" ".join(current_line))
                                current_line = []
                        else:
                            current_line.append(t.value)
                        self.pos += 1
                    else:
                        self.consume('RBRACE')
                
                # Voeg eventuele resterende instructies toe
                if current_line:
                    asm_lines.append(" ".join(current_line))
                
                # Sla de regels op met harde newlines en nette inspringing
                joined_asm = "\n    ".join(asm_lines)
                body.append(AsmBlockNode(joined_asm))
            else:
                self.pos += 1 
                
        self.consume('RBRACE')
        return FunctionNode(func_name, body)

class SternCompiler:
    def __init__(self, ast_root):
        self.ast_root = ast_root
        self.symbol_table = {}
        self.memory_pointer = 0  # Start na de JMP opmerkingen
        self.generated_asm = []

    def compile(self) -> str:
        # Pass 1: Scan de MAP sectie en bouw de Symbol Table met TYPE-informatie
        for node in self.ast_root:
            if isinstance(node, MapSectionNode):
                self.process_map(node)

        # Pass 2: Genereer én valideer de PROGRAM code
        for node in self.ast_root:
            if isinstance(node, ProgramSectionNode):
                self.process_program(node)

        return "\n".join(self.generated_asm)

    def process_map(self, node: MapSectionNode):
        self.generated_asm.append("; --- SYSTEM MAP GENERATED START ---")
        self.generated_asm.append("JMP main")
        self.memory_pointer += 1
        
        for name, info in node.definitions.items():
            if info['type'] == 'RES':
                # Een RES levert een geheugenadres (pointer) op
                self.symbol_table[name] = {'value': self.memory_pointer, 'type': 'ADDRESS'}
                self.memory_pointer += info['value']
            elif info['type'] in ('CONST', 'IO'):
                self.symbol_table[name] = {'value': info['value'], 'type': info['type']}
                
    def process_program(self, node: ProgramSectionNode):
        self.generated_asm.append("\n; --- SYSTEM PROGRAM CODE ---")
        for func in node.functions:
            self.generated_asm.append(f"{func.name}:")
            for block in func.body:
                if isinstance(block, AsmBlockNode):
                    # Verwerk en valideer de ASM regels één voor één
                    lines = block.code.split('\n')
                    for line in lines:
                        clean_line = line.strip()
                        if not clean_line: continue
                        
                        validated_line = self.validate_and_resolve_asm(clean_line)
                        self.generated_asm.append(f"    {validated_line}")

    def validate_and_resolve_asm(self, asm_line: str) -> str:
        parts = asm_line.split()
        if not parts: return ""
        
        mnemonic = parts[0].upper()
        args = parts[1:]
        
        # Haal symbolen op en controleer ze semantisch
        resolved_args = []
        for arg in args:
            # Strip eventuele komma's weg voor de check
            clean_arg = arg.rstrip(',')
            has_comma = arg.endswith(',')
            
            if clean_arg in self.symbol_table:
                sym_info = self.symbol_table[clean_arg]
                
                # --- SEMANTISCHE VALIDATIE EN TYPE CHECKING ---
                if mnemonic == 'LDI':
                    if sym_info['type'] == 'ADDRESS':
                        raise SyntaxError(
                            f"Semantische Fout: '{clean_arg}' is gedefinieerd als RES (ADDRESS). "
                            f"LDI verwacht een CONST of NUMBER, geen adreslocatie!"
                        )
                
                if mnemonic == 'OUT':
                    if sym_info['type'] != 'IO':
                        raise SyntaxError(
                            f"Semantische Fout: OUT verwacht een IO poort. '{clean_arg}' is een {sym_info['type']}."
                        )
                
                # Als de check slaagt, vervang de waarde
                val_str = str(sym_info['value'])
                resolved_args.append(val_str + "," if has_comma else val_str)
            else:
                # Het is een register (B) of een hard-coded getal
                resolved_args.append(arg)
                
        return f"{mnemonic} {' '.join(resolved_args)}"





# ======= test main from here ======
def print_ast(node, indent=0):
    space = "  " * indent
    
    if isinstance(node, MapSectionNode):
        print(f"{space}└─ [MapSectionNode]")
        for name, info in node.definitions.items():
            print(f"{space}   ├─ {name}: {info['type']} (Value: {info['value']})")
            
    elif isinstance(node, ProgramSectionNode):
        print(f"{space}└─ [ProgramSectionNode]")
        for func in node.functions:
            print_ast(func, indent + 1)
            
    elif isinstance(node, FunctionNode):
        print(f"{space}├─ [FunctionNode] Name: {node.name}")
        for child in node.body:
            print_ast(child, indent + 2)
            
    elif isinstance(node, AsmBlockNode):
        print(f"{space}├─ [AsmBlockNode]")
        # Splits de multi-line string op in losse regels en haal loze witruimte weg
        lines = [line.strip() for line in node.code.strip().split('\n') if line.strip()]
        for line in lines:
            # Elke regel krijgt nu netjes de verticale boom-lijn mee
            print(f"{space}│    Code: {line}")

def main():
    test_code = """
    // SternZ32G Architectuur Test File
    MAP {
        CONST   counter    42
        IO      X_value    2
    }

    PROGRAM {
        void main() {
            {
                LDI B counter
                INC B
                CONTEXT B proces_io
            }
        }
        
        void process_io() {
            {
                OUT B X_value
                CLOSE
            }
        }
    }
    """

    print("=" * 60)
    print(" SternZ32G Compiler Toolchain - Parser Test Suite ")
    print("=" * 60)

    try:
        print("[1/4] Tokenizing broncode...")
        tokens = lex(test_code)
        print(f" -> Succesvol {len(tokens)} tokens gegenereerd.")
        
        print("\n[2/4] Bouwen van Abstract Syntax Tree (AST)...")
        parser = OrchestratorParser(tokens)
        ast_root = parser.parse()
        print(" -> AST succesvol gegenereerd zonder syntaxfouten.")

        print("\n[3/4] AST Visualisatie:")
        print("─" * 40)
        for top_level_node in ast_root:
            print_ast(top_level_node)
        print("─" * 40)

        # --- HIER PLUGGEN WE DE COMPILER IN ---
        print("\n[4/4] Activeren van Codegeneratie...")
        compiler = SternCompiler(ast_root)
        output_asm = compiler.compile()
        
        print("\nGegenereerde Ruwe Assembly Output:")
        print("=" * 60)
        print(output_asm)
        print("=" * 60)

        print("\n[STATUS] Test succesvol afgerond. De keten werkt van broncode tot output.")

    except SyntaxError as e:
        print(f"\n[PARSER FOUT] Er is een fout opgetened tijdens het ontleden:")
        print(f" -> {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[CRITISCHE FOUT] Onverwachte fout: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()