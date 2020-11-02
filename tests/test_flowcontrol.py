from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string
from CSBCAsm.Errors import *

def test_if_z():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    if z_set
        ldy #0x00
        if z_clear
            ldx #0xff
        endif
    endif
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0xD0, 0x06, 0xA0, 0x00, 0xF0, 0x02, 0xA2, 0xFF])

def test_if_c():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    if c_set
        ldy #0x00
        if c_clear
            ldx #0xff
        endif
    endif
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x90, 0x06, 0xA0, 0x00, 0xB0, 0x02, 0xA2, 0xFF])

def test_if_v():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    if v_set
        ldy #0x00
        if v_clear
            ldx #0xff
        endif
    endif
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x50, 0x06, 0xA0, 0x00, 0x70, 0x02, 0xA2, 0xFF])

def test_if_n():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    if n_set
        ldy #0x00
        if n_clear
            ldx #0xff
        endif
    endif
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x10, 0x06, 0xA0, 0x00, 0x30, 0x02, 0xA2, 0xFF])

def test_if_error():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    if foo
        ldx #0xff
    endif
'''
    try:
        code = assemble_string(program_string)
    except InvalidParameterError:
        pass

def test_ifelse_z():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    if z_set
        ldy #0x00
        if z_clear
            ldx #0xff
        else
            ldx #0x01
        endif
    else
        ldy #0x01
    endif
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0xD0, 0x0C, 0xA0, 0x00, 0xF0, 0x04, 0xA2, 0xFF, 0x80, 0x02, 0xA2, 0x01, 0x80, 0x02, 0xA0, 0x01])

def test_dountil_z():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    do
        do
            inc a
        until z_clear
    until z_set
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x1A, 0xF0, 0xFD, 0xD0, 0xFB])

def test_dountil_c():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    do
        do
            inc a
        until c_clear
    until c_set
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x1A, 0xB0, 0xFD, 0x90, 0xFB])

def test_dountil_v():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    do
        do
            inc a
        until v_clear
    until v_set
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x1A, 0x70, 0xFD, 0x50, 0xFB])

def test_dountil_n():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    do
        do
            inc a
        until n_clear
    until n_set
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x1A, 0x30, 0xFD, 0x10, 0xFB])

def test_doforever():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    do
        inc a
    forever
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0x1A, 0x80, 0xFD])


def test_case_a():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    lda #0x01
    switch a
        case #0x01
            nop
        case #0x02
            inx
        case #0x03
            iny
    endswitch
    .a16
    lda #0x4401
    switch a
        case #0x4401
            nop
        case #0x4402
            inx
        case #0x4403
            iny
    endswitch
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x01, 0xC9, 0x01, 0xD0, 0x01, 0xEA, 0x80, 0x0C,
                                                            0xC9, 0x02, 0xD0, 0x01, 0xE8, 0x80, 0x05,
                                                            0xC9, 0x03, 0xD0, 0x01, 0xC8,
                                                0xA9, 0x01, 0x44, 0xC9, 0x01, 0x44, 0xD0, 0x01, 0xEA, 0x80, 0x0E,
                                                                  0xC9, 0x02, 0x44, 0xD0, 0x01, 0xE8, 0x80, 0x06,
                                                                  0xC9, 0x03, 0x44, 0xD0, 0x01, 0xC8
                                               ])

def test_case_x():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    ldx #0x01
    switch x
        case #0x01
            nop
        case #0x02
            inx
        case #0x03
            iny
    endswitch
    .i16
    ldx #0x4401
    switch x
        case #0x4401
            nop
        case #0x4402
            inx
        case #0x4403
            iny
    endswitch
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA2, 0x01, 0xE0, 0x01, 0xD0, 0x01, 0xEA, 0x80, 0x0C,
                                                            0xE0, 0x02, 0xD0, 0x01, 0xE8, 0x80, 0x05,
                                                            0xE0, 0x03, 0xD0, 0x01, 0xC8,
                                                0xA2, 0x01, 0x44, 0xE0, 0x01, 0x44, 0xD0, 0x01, 0xEA, 0x80, 0x0E,
                                                                  0xE0, 0x02, 0x44, 0xD0, 0x01, 0xE8, 0x80, 0x06,
                                                                  0xE0, 0x03, 0x44, 0xD0, 0x01, 0xC8
                                               ])

def test_case_y():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    ldy #0x01
    switch y
        case #0x01
            nop
        case #0x02
            inx
        case #0x03
            iny
    endswitch
    .i16
    ldy #0x4401
    switch y
        case #0x4401
            nop
        case #0x4402
            inx
        case #0x4403
            iny
    endswitch
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA0, 0x01, 0xC0, 0x01, 0xD0, 0x01, 0xEA, 0x80, 0x0C,
                                                            0xC0, 0x02, 0xD0, 0x01, 0xE8, 0x80, 0x05,
                                                            0xC0, 0x03, 0xD0, 0x01, 0xC8,
                                                0xA0, 0x01, 0x44, 0xC0, 0x01, 0x44, 0xD0, 0x01, 0xEA, 0x80, 0x0E,
                                                                  0xC0, 0x02, 0x44, 0xD0, 0x01, 0xE8, 0x80, 0x06,
                                                                  0xC0, 0x03, 0x44, 0xD0, 0x01, 0xC8
                                               ])

def test_while_c_set():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    sec
    lda #0
    while c_set
        inc a
        cmp #0x20
        if z_set
            sec
        endif
    endwhile
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0x38, 0xA9, 0x00, 0x90, 0x08, 0x1A, 0xC9, 0x20, 0xD0, 0x01, 0x38, 0xB0, 0xF8])

