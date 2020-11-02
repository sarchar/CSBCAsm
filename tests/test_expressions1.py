
from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string

def test_addition():
    program = parse_string("\tplaceholder 5 + 42")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Add) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 47
    assert program_ast.left.eval() == 5
    assert program_ast.right.eval() == 42

def test_unary_addition():
    program = parse_string("\tplaceholder -5 + +42")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Add) and isinstance(program_ast.left, ParserAST.UnaryOp_Negate) and isinstance(program_ast.right, ParserAST.UnaryOp_Posigate)
    assert program_ast.eval() == 37 
    assert program_ast.left.eval() == -5
    assert program_ast.right.eval() == 42

def test_subtraction():
    program = parse_string("\tplaceholder 114-32")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Sub) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 82
    assert program_ast.left.eval() == 114
    assert program_ast.right.eval() == 32

def test_multiplication():
    program = parse_string("\tplaceholder 71 *9")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Mul) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 639
    assert program_ast.left.eval() == 71
    assert program_ast.right.eval() == 9

def test_division():
    program = parse_string("\tplaceholder 169 / 3")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Div) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 56
    assert program_ast.left.eval() == 169
    assert program_ast.right.eval() == 3

def test_power():
    program = parse_string("\tplaceholder 3 ** 4")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Pow) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 81
    assert program_ast.left.eval() == 3
    assert program_ast.right.eval() == 4

def test_modulus():
    program = parse_string("\tplaceholder 117 % 6")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Mod) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 3
    assert program_ast.left.eval() == 117
    assert program_ast.right.eval() == 6

def test_and():
    program = parse_string("\tplaceholder 0b1111_0001 & 0xAF")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_And) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 0xA1
    assert program_ast.left.eval() == 0xF1
    assert program_ast.right.eval() == 0xAF

def test_xor():
    program = parse_string("\tplaceholder 0b1111_0001 ^ 0xAF")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Xor) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 0x5E
    assert program_ast.left.eval() == 0xF1
    assert program_ast.right.eval() == 0xAF

def test_or():
    program = parse_string("\tplaceholder 0b1111_0001 | 0xAF")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Or) and isinstance(program_ast.left, ParserAST.Number) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 0xFF
    assert program_ast.left.eval() == 0xF1
    assert program_ast.right.eval() == 0xAF

def test_not():
    program = parse_string("\tplaceholder ~0b1111_0001 | ~0xAF")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Or) and isinstance(program_ast.left, ParserAST.UnaryOp_Not) and isinstance(program_ast.right, ParserAST.UnaryOp_Not)
    assert program_ast.eval() == 0x5E
    assert program_ast.left.eval() == 0x0E
    assert program_ast.right.eval() == 0x50

def test_left_shift():
    program = parse_string("\tplaceholder ~0b0111_0001 << 2")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_LeftShift) and isinstance(program_ast.left, ParserAST.UnaryOp_Not) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 0x238
    assert program_ast.left.eval() == 0x8E
    assert program_ast.right.eval() == 2

def test_right_shift():
    program = parse_string("\tplaceholder ~0b0111_0001 >> 3")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_RightShift) and isinstance(program_ast.left, ParserAST.UnaryOp_Not) and isinstance(program_ast.right, ParserAST.Number)
    assert program_ast.eval() == 0x11
    assert program_ast.left.eval() == 0x8E
    assert program_ast.right.eval() == 3

def test_parens1():
    program = parse_string("\tplaceholder (42)")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    # twice, because parenthesis only hold expression lists
    assert isinstance(program_ast, ParserAST.ExpressionList) and isinstance(program_ast.value[0], ParserAST.Number)
    assert program_ast.eval() == 42

def test_parens2():
    program = parse_string("\tplaceholder (42 - -8)")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.ExpressionList) and isinstance(program_ast.value[0], ParserAST.BinaryOp_Sub)
    assert program_ast.eval() == 50

def test_parens3():
    program = parse_string("\tplaceholder -(5 * 5) * 3")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.BinaryOp_Mul) and isinstance(program_ast.left, ParserAST.UnaryOp_Negate) and isinstance(program_ast.left.value, ParserAST.ExpressionList)
    assert program_ast.left.value.eval() == 25
    assert program_ast.eval() == -75

def test_parens4():
    program = parse_string("\tplaceholder -((5 * 5) * (3 + 1))")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList)
    program_ast = program_ast.value[0]

    assert isinstance(program_ast, ParserAST.UnaryOp_Negate) and isinstance(program_ast.value, ParserAST.ExpressionList) \
           and isinstance(program_ast.value.value[0], ParserAST.BinaryOp_Mul) \
           and isinstance(program_ast.value.value[0].left, ParserAST.ExpressionList) \
           and isinstance(program_ast.value.value[0].right, ParserAST.ExpressionList) 
    assert program_ast.eval() == -100

def test_expression_list():
    program = parse_string("\tplaceholder (5, 10 * 2), 15")

    program_ast = program[0].statement_list.value[0]
    assert isinstance(program_ast, ParserAST.Statement)
    program_ast = program_ast.operands

    assert isinstance(program_ast, ParserAST.ExpressionList) and len(program_ast.value) == 2 \
           and isinstance(program_ast.value[0], ParserAST.ExpressionList) \
           and isinstance(program_ast.value[1], ParserAST.Number) \
           and isinstance(program_ast.value[0].value[0], ParserAST.Number) \
           and isinstance(program_ast.value[0].value[1], ParserAST.BinaryOp_Mul)
    assert program_ast.eval() == [[5, 20], 15]

#test_parens1()
