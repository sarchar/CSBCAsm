from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string


def test_equate_simple():
    program_string = '''
COUNTER  = 0x00
COUNTER2 = (COUNTER + 1)
COUNTER3 = 0x1001
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    inc COUNTER2  /* direct page */
    inc COUNTER3  /* absolute */
    jmp _init
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xE6, 0x01, 0xEE, 0x01, 0x10, 0x4C, 0x00, 0x00])


