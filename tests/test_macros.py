from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string, save_code_as_intel_hex
from CSBCAsm.Errors import *

def test_macro_nop():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
insert_nop: .macro
    nop
    .endmacro
main:
    insert_nop
    insert_nop
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xEA, 0xEA])


def test_macro_cpu16():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
cpu16: .macro
    rep #%00110000
    .a16
    .i16
    .endmacro
main:
    cpu16
    lda #$1234
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xC2, 0x30, 0xA9, 0x34, 0x12])

def test_macro_error_nested():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
cpu16: .macro
foo: .macro
    .endmacro
main:
    cpu16
    lda #$1234
'''
    try:
        code = assemble_string(program_string)
    except MacroError:
        pass

def test_macro_error_endmacro():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
    .endmacro
'''
    try:
        code = assemble_string(program_string)
    except MacroError:
        pass

def test_macro_nested():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
inside: .macro
    ldx #$02
    .endmacro
outside: .macro
    lda #$01
    inside
    .endmacro
main:
    outside
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0xA2, 0x02])

def test_macro_parameters1():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
inc_two: .macro one, two
    inc one
    inc two
    .endmacro
main:
    inc_two $0000, $0002
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xEE, 0x00, 0x00, 0xEE, 0x02, 0x00])

def test_macro_parameters2():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
inc_two: .macro one
    inc <one
    inc >one
    .endmacro
main:
    inc_two (data * 2)
    .org $CABC
data: .db 0x0
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xE6, 0xBC*2 & 0xFF, 0xE6, (0xCA*2+1) & 0xFF])

def test_macro_varargs():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
    inc \\0
    inc \\1
    .endmacro
main:
    varargs 0xEE, 0x0101, 0xF00D
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xE6, 0xEE, 0xEE, 0x01, 0x01])

def test_macro_varargs_len():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro x, ...
    lda #(\\L & 0xFF)
    .endmacro
main:
    varargs 0x00, 0xEE, 0x0101, 0xF00D
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x03])

def test_macro_varargs_len2():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro tmp, ...
        .if \\L != 1
            lda #(\\1 & 0xFF)
        .endif
    .endmacro
main:
    varargs 0x12, main
    varargs 0x00, 0xEE, 0xF00D
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x0D])

def test_macro_varargs_len3_ifelse():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro tmp, ...
        .if \\L != 1
            lda #(\\1 & 0xFF)
        .else
            ldx #(\\0 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs 0x12, main
    varargs 0x00, 0xEE, 0xF00D
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA2, 0x34, 0xA9, 0x0D])

def test_macro_varargs_len3_ifelif():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro tmp, ...
        .if \\L == 1
            lda #(\\0 & 0xFF)
        .elif \\L == 2
            ldy #(\\1 & 0xFF)
        .else
            ldx #(\\2 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs 0x12, main
    varargs 0x12, main, 0xFF
    varargs 0x00, 0x12, 0xEE, 0xF00D
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34, 0xA0, 0xFF, 0xA2, 0x0D])

def test_macro_lt_gt():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
        .if \\L < 5
            lda #(\\0 & 0xFF)
        .endif
        .if \\L > 1
            ldx #(\\0 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs main, 0x00
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34, 0xA2, 0x34])

def test_macro_lte_gte():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
        .if \\L <= 1
            lda #(\\0 & 0xFF)
        .endif
        .if \\L >= 1
            ldx #(\\0 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs main
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34, 0xA2, 0x34])

def test_macro_not_lte_gte():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
        .if !(\\L > 1)
            lda #(\\0 & 0xFF)
        .endif
        .if !(\\L < 1)
            ldx #(\\0 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs main
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34, 0xA2, 0x34])

def test_macro_and_not_lt_gt():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
        .if !(\\L > 1) && !(\\L < 1)
            lda #(\\0 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs main
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34])

def test_macro_or_not_lt_gt():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
        .if !((\\L > 1) || (\\L < 1))
            lda #(\\0 & 0xFF)
        .endif
    .endmacro
    .org 0x1234
main:
    varargs main
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34])

def test_valoop():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
varargs: .macro ...
        .i16
        ldy #$1234
        .valoop
            lda (\\i), y
            inc \\v
        .endvaloop
    .endmacro
    .org 0x1234
main:
    varargs 0x11, 0x22, 0x33, 0x44
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA0, 0x34, 0x12,
                                                0xB1, 0x00, 0xE6, 0x11,
                                                0xB1, 0x01, 0xE6, 0x22,
                                                0xB1, 0x02, 0xE6, 0x33,
                                                0xB1, 0x03, 0xE6, 0x44])

