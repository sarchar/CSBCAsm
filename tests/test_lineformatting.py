from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string

test_a_number_src = '''
    .segment "formatting", 0x0000, 0x10000
    .formatting
    .org start

    .db 5
label: .db 5
label2:
    .db 5
    .db 5 ; with comment
label3: .db 5 ; with comment

'''

def test_comment1():
    lexer = Lexer.CreateLexer()
    tokens = list(lexer.lex("; This is a comment"))
    assert len(tokens) == 0, tokens

def test_comment2():
    program = parse_string("\tplaceholder (42) ; This is the answer")

    stmt = program[0].statement_list.value[0]
    operands = stmt.operands
    assert isinstance(operands, ParserAST.ExpressionList)
    assert operands.value[0].eval() == 42

def test_comment3():
    program = parse_string("    ; This is a comment")
    assert len(program) == 1 and program[0].label_declaration is None and len(program[0].statement_list.value) == 0

def test_multiple_statements1():
    program = parse_string("\tnop : jmp\n")
    assert isinstance(program[0], ParserAST.Line) and len(program[0].statement_list.value) == 2
    for statement in program[0].statement_list.value:
        assert len(statement.operands.value) == 0

def test_multiple_statements2():
    lexer = Lexer.CreateLexer()
    parser = Parser.CreateParser()

    tokens = lexer.lex("\tnop jmp bra bcc")
    try:
        program_ast = parser.parse(tokens)
    except Parser.ParseError:
        pass

def test_multiple_statements3():
    lexer = Lexer.CreateLexer()
    parser = Parser.CreateParser()

    program = parse_string("\tnop : jmp $03:1234 : bra : bcc")

def test_multiple_statements4():
    lexer = Lexer.CreateLexer()
    parser = Parser.CreateParser()

    try:
        program = parse_string("\tnop : jmp $03: 1234 : bra : bcc")
    except Parser.ParseError:
        pass

def test_multiple_statements5():
    lexer = Lexer.CreateLexer()
    parser = Parser.CreateParser()

    try:
        program = parse_string("\tnop : bra :")
    except Parser.ParseError:
        pass

def test_label_declaration1():
    program = parse_string("label: placeholder")
    assert isinstance(program[0], ParserAST.Line)
    assert program[0].label_declaration is not None
    assert len(program[0].statement_list.value) == 1

def test_label_declaration2():
    program = parse_string(" label: placeholder")
    assert isinstance(program[0], ParserAST.Line)
    assert program[0].label_declaration is None
    assert len(program[0].statement_list.value) == 2

def test_label_declaration3():
    program = parse_string("label:")
    assert isinstance(program[0], ParserAST.Line)
    assert program[0].label_declaration is not None and program[0].label_declaration.value == "label"
    assert len(program[0].statement_list.value) == 0

def test_label_declaration4():
    program = parse_string("label")
    assert isinstance(program[0], ParserAST.Line)
    assert program[0].label_declaration is not None and program[0].label_declaration.value == "label"
    assert len(program[0].statement_list.value) == 0

def test_label_declaration5():
    try:
        program = parse_string("label nop") # colon required to define label
        assert False
    except Parser.ParseError:
        pass

