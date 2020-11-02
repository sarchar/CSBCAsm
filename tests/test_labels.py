from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string


def test_simple():
    program = parse_string(" jmp here")

    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands

    assert isinstance(operands, ParserAST.ExpressionList)
    name = operands.value[0]

    assert isinstance(name, ParserAST.Name)
    referenced_names = name.find_referenced_names()
    assert "here" in referenced_names
    assert len(referenced_names["here"]) == 1
    assert referenced_names["here"] == [name]

    try:
        v = operands.eval() # should raise an exception
        raise Exception("eval succeeded with v =", v)
    except ParserAST.NameNotEvaluatableError:
        pass

def test_add():
    program = parse_string("\tjmp here+5")

    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands

    assert isinstance(operands, ParserAST.ExpressionList)
    bop = operands.value[0]

    assert isinstance(bop, ParserAST.BinaryOp_Add)

    referenced_names = bop.find_referenced_names()
    assert "here" in referenced_names
    assert len(referenced_names["here"]) == 1

    try:
        v = bop.eval() # should raise an exception
        raise Exception("eval succeeded with v =", v)
    except ParserAST.NameNotEvaluatableError:
        pass

def test_two():
    program = parse_string("    jmp (neither_here + nor_there) * neither_here")

    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands

    assert isinstance(operands, ParserAST.ExpressionList)
    referenced_names = operands.find_referenced_names()

    assert "neither_here" in referenced_names
    assert len(referenced_names["neither_here"]) == 2
    assert "nor_there" in referenced_names
    assert len(referenced_names["nor_there"]) == 1

    try:
        v = operands.eval() # should raise an exception
        raise Exception("eval succeeded with v =", v)
    except ParserAST.NameNotEvaluatableError:
        pass

def test_replace_and_evaluate():
    program = parse_string("\n\tlda (age/2)+7")

    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands
    assert isinstance(operands, ParserAST.ExpressionList)

    referenced_names = operands.find_referenced_names()
    assert "age" in referenced_names
    assert len(referenced_names["age"]) == 1

    n = ParserAST.Number(30, 'dec', 1)
    for rl in referenced_names['age']:
        rl.set_actual_value(n)

    assert operands.eval() == 22

def test_replace_and_evaluate2():
    program = parse_string("\n\tlda answer*answer")

    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands

    referenced_names = operands.find_referenced_names()
    n = ParserAST.Number(42, 'dec', 1)
    for rl in referenced_names['answer']:
        rl.set_actual_value(n)

    assert operands.eval() == 1764

def test_this_label():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   lda #(.+2 & 0xFF)
        ldy .-2, X
'''

    co = assemble_string(program_string)
    assert co['code']['code'][0][1] == bytes([0xA9, 0x02, 0xBC, 0x00, 0xC0])

def test_this_label_branch():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   bra .
'''

    co = assemble_string(program_string)
    assert co['code']['code'][0][1] == bytes([0x80, 0xFE])

def test_tmp_label():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   bra @1
        jmp main
@1:     bra .
@1:     bra @1
'''

    co = assemble_string(program_string)
    assert co['code']['code'][0][1] == bytes([0x80, 0x03, 0x4C, 0x00, 0xC0, 0x80, 0xFE, 0x80, 0xFE])

def test_tmp_label2():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   bra @1
        jmp main
@1:     bra @2+
@2:     bra @1-
@1:     nop
'''

    co = assemble_string(program_string)
    print(co)
    assert co['code']['code'][0][1] == bytes([0x80, 0x03, 0x4C, 0x00, 0xC0, 0x80, 0x00, 0x80, 0xFC, 0xEA])

def test_tmp_label3():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   bra @1
        jmp main
@1:     bra @1+
@1:     bra @1-
@1:     nop
'''

    co = assemble_string(program_string)
    print(co)
    assert co['code']['code'][0][1] == bytes([0x80, 0x03, 0x4C, 0x00, 0xC0, 0x80, 0x00, 0x80, 0xFE, 0xEA])

