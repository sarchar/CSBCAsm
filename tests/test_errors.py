from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string, save_code_as_intel_hex
from CSBCAsm.Errors import *


def test_segment_redefinition():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   .segment "code", 0x8000, 0x8000, 0
'''

    try:
        co = assemble_string(program_string)
    except SegmentRedefinitionError:
        pass

def test_no_segment():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        nop
        .code
        .org start
main:   nop
'''

    try:
        co = assemble_string(program_string)
    except NoSegmentError:
        pass

def test_no_compiler_directive_labels():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
.main:  nop
'''

    try:
        co = assemble_string(program_string)
    except ReservedNameError:
        pass

def test_label_redefinition():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:  nop
        .code
main:  inc $ff
'''

    try:
        co = assemble_string(program_string)
    except LabelRedefinitionError:
        pass

def test_label_reserved():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
a:      jmp a
'''

    try:
        co = assemble_string(program_string)
    except ReservedNameError:
        pass

def test_label_equate_redefine():
    program_string = '''
        VALUE = 5
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
VALUE:      jmp VALUE
'''

    try:
        co = assemble_string(program_string)
    except LabelRedefinitionError:
        pass

def test_equate_bad_expression():
    program_string = '''
        VALUE = "Foobar"
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   jmp main
'''

    try:
        co = assemble_string(program_string)
    except EquateDefinitionError:
        pass

