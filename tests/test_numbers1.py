
from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string

def test_lexer_dec1():
    lexer = Lexer.CreateLexer()
    for i in range(0, 1000):
        tokens = list(lexer.lex("{}".format(i)))
        assert tokens[0].gettokentype() == 'DEC_NUMBER'
        assert tokens[0].getstr() == "{}".format(i)

def test_parser_dec1():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder {}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.Number)
        assert expression.eval() == i
        assert expression.base == 'dec'
        if i < 256:
            assert expression.stated_byte_size == 1, str(i)
        else:
            assert expression.stated_byte_size == 2, str(i)

def test_parser_negative_dec1():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder -{}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.UnaryOp_Negate) and isinstance(expression.value, ParserAST.Number)
        assert expression.eval() == -i
        assert expression.collapse().eval() == -i
        assert expression.value.base == 'dec'
        #TODO: test stated_byte_size ?

def test_lexer_hex1():
    lexer = Lexer.CreateLexer()
    for i in range(0, 1000):
        tokens = list(lexer.lex("${:x}".format(i)))
        assert tokens[0].gettokentype() == 'HEX_NUMBER'
        assert tokens[0].getstr() == "${:x}".format(i)
        tokens = list(lexer.lex("0x{:X}".format(i)))
        assert tokens[0].gettokentype() == 'HEX_NUMBER'
        assert tokens[0].getstr() == "0x{:X}".format(i)

def test_parser_hex1():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder ${:x}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.Number)
        assert expression.eval() == i
        assert expression.base == 'hex'
        if i < 256:
            assert expression.stated_byte_size == 1, str(i)
        else:
            assert expression.stated_byte_size == 2, str(i)
        program = parse_string("\tplaceholder 0x{:X}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.Number)
        assert expression.eval() == i
        assert expression.base == 'hex'
        if i < 256:
            assert expression.stated_byte_size == 1, str(i)
        else:
            assert expression.stated_byte_size == 2, str(i)
    program = parse_string("\tplaceholder 0x00F")
    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands
    assert isinstance(operands, ParserAST.ExpressionList)
    expression = operands.value[0]
    assert isinstance(expression, ParserAST.Number)
    assert expression.eval() == 0xF
    assert expression.base == 'hex'
    assert expression.stated_byte_size == 2, str(i)

def test_parser_hex2():
    import random
    for i in range(0, 256):
        b = random.randrange(0, 0xFFFF)
        program = parse_string("\tplaceholder ${:02x}:{:04x}".format(i, b))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.Number)
        assert expression.eval() == ((i << 16) | b)
        assert expression.base == 'hex'
        assert expression.stated_byte_size == 3, str(i)

def test_parser_negative_hex1():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder -${:x}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.UnaryOp_Negate) and isinstance(expression.value, ParserAST.Number)
        assert expression.eval() == -i
        assert expression.collapse().eval() == -i
        assert expression.value.base == 'hex'
        #if i < 256:
        #    assert expression.stated_byte_size == 1, str(i)
        #else:
        #    assert expression.stated_byte_size == 2, str(i)
        program = parse_string("\tplaceholder -0x{:X}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.UnaryOp_Negate) and isinstance(expression.value, ParserAST.Number)
        assert expression.eval() == -i
        assert expression.collapse().eval() == -i
        assert expression.value.base == 'hex'
        #if i < 256:
        #    assert expression.stated_byte_size == 1, str(i)
        #else:
        #    assert expression.stated_byte_size == 2, str(i)
    program = parse_string("\tplaceholder -0x00F")
    statement = program[0].statement_list.value[0]
    assert isinstance(statement, ParserAST.Statement)
    operands = statement.operands
    assert isinstance(operands, ParserAST.ExpressionList)
    expression = operands.value[0]
    assert isinstance(expression, ParserAST.UnaryOp_Negate) and isinstance(expression.value, ParserAST.Number)
    assert expression.eval() == -0xF
    assert expression.value.base == 'hex'
    #assert expression.stated_byte_size == 2, str(i)

def test_lexer_hex2():
    try:
        program = parse_string("\tinc $::::")
    except ValueError:
        pass

def test_lexer_oct1():
    lexer = Lexer.CreateLexer()
    for i in range(0, 1000):
        tokens = list(lexer.lex("0o{:o}".format(i)))
        assert tokens[0].gettokentype() == 'OCT_NUMBER'
        assert tokens[0].getstr() == "0o{:o}".format(i)

def test_parser_oct1():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder 0o{:o}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.Number)
        assert expression.eval() == i
        assert expression.base == 'oct'

def test_parser_oct2():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder &{:o}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.Number)
        assert expression.eval() == i
        assert expression.base == 'oct'

def test_parser_negative_oct1():
    for i in range(0, 1000):
        program = parse_string("\tplaceholder -0o{:o}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert expression.eval() == -i
        assert expression.collapse().eval() == -i
        assert expression.value.base == 'oct'

def test_lexer_bin1():
    lexer = Lexer.CreateLexer()
    for i in range(0, 256):
        tokens = list(lexer.lex("0b{:b}".format(i)))
        assert tokens[0].gettokentype() == 'BIN_NUMBER'
        assert tokens[0].getstr() == "0b{:b}".format(i)

def test_parser_bin1():
    for i in range(0, 512):
        program = parse_string("\tplaceholder 0b{:b}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert expression.eval() == i
        assert expression.base == 'bin'
        if i < 256:
            assert expression.stated_byte_size == 1, str(i)
        else:
            assert expression.stated_byte_size == 2, str(i)

def test_parser_bin2():
    for i in range(0, 512):
        program = parse_string("\tplaceholder %{:b}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert expression.eval() == i
        assert expression.base == 'bin'
        if i < 256:
            assert expression.stated_byte_size == 1, str(i)
        else:
            assert expression.stated_byte_size == 2, str(i)

def test_parser_negative_bin1():
    for i in range(0, 512):
        program = parse_string("\tplaceholder -0b{:b}".format(i))
        statement = program[0].statement_list.value[0]
        assert isinstance(statement, ParserAST.Statement)
        operands = statement.operands
        assert isinstance(operands, ParserAST.ExpressionList)
        expression = operands.value[0]
        assert isinstance(expression, ParserAST.UnaryOp_Negate) and isinstance(expression.value, ParserAST.Number)
        assert expression.eval() == -i
        assert expression.collapse().eval() == -i
        assert expression.value.base == 'bin'
        #if i < 256:
        #    assert program_ast.stated_byte_size == 1, str(i)
        #else:
        #    assert program_ast.stated_byte_size == 2, str(i)

