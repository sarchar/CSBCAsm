from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string

def test_nop():
    program_string = '''
    .segment "code", 0x0000, 0x10000, 0
    .code
    .org start
_init:
    nop
    .db 0x4C, 0x00, 0x00 ; JMP 0x0000
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xEA, 0x4C, 0x00, 0x00])

def test_bcc_label():
    program_string = '''
        .segment "code", 0x0000, 0x10000, 0
        .code
        .org start
loop:   clc
        bcc loop ; loop forever
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0x18, 0x90, 0xFD])

def test_lda_abs():
    program_string = '''
        .segment "code", 0x0000, 0x10000, 0
        .code
        .org start
loop:   lda const
        bcc loop ; loop forever
const:  .dw $BEEF
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xAD, 0x05, 0x00, 0x90, 0xFB, 0xEF, 0xBE])

def test_program_counter():
    program_string = '''
        ; segments define blocks of code and data and also specify where in the output "memory" the blocks reside.
        ;          name   start   size   file_offset
        .segment "code", $C000, $3FE0, $0000
        .segment "vectors16", $FFE0, $10, $3FE0
        .segment "vectors8", $FFF0, $10, $3FF0

        ; .org is used within a segment and is related to the 'start' of the specified segment (i.e., specifying or letting your code run out of the segment bounds will generate an error)
        .code ; TODO this comment is a workaround to my shoddy parser knowledge.
        .org $C000

hello_world_str:
        .dw 0x1234, $5678
        .db "Hello, world!", 0

        .global _init
_init: 
        sei      ; disable interrupts
        lda #$00 ; clear A
        sta $00  ; reset our counters to 0
        sta $01
        sta $02
_a:     inc $00  ; increment low byte of counter 1
        bne _a
        inc $01  ; increment high byte of counter 1
        bne _a
        inc $02  ; set our done flag
_b:     jmp _b

        .org $C080
_d:     clc
        bcc _d

        .vectors16 ; TODO this comment is a workaround to my shoddy parser knowledge.
        .org start ; TODO want to support default .org.  Maybe if no .org is specified, defaults to the start of the defined segment

        .vectors8 ; TODO this comment is a workaround to my shoddy parser knowledge.
        .org start
        .dw 0
        .dw 0
        .dw 0
        .dw 0
v_ABORT: .dw 0
v_NMI:   .dw 0
v_RESET: .dw _init
v_IRQ:   .dw 0
'''
    code = assemble_string(program_string)

def test_indirect_jump_and_label_math():
    program_string = '''
LO_ADDR = $04
HI_ADDR = $05
INDIR   = $0004
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
        .global loop
loop:   lda #(loop & 0xFF)
        sta LO_ADDR
        lda #((loop & 0xFF00) >> 8)
        sta HI_ADDR
        jmp (INDIR)  // Loop forever

        .segment "vectors8", $FFF0, $10, $3FF0
        .vectors8
        .org $FFFC
reset:
        .dw loop
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x00, 0x85, 0x04, 0xA9, 0xC0, 0x85, 0x05, 0x6C, 0x04, 0x00])

def test_indirect_jump_and_lohi_byte():
    program_string = '''
LO_ADDR = $04
HI_ADDR = $05
INDIR   = $0004
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
        .global loop
loop:   lda #<loop
        sta LO_ADDR
        lda #>loop
        sta HI_ADDR
        jmp (INDIR)  // Loop forever

        .segment "vectors8", $FFF0, $10, $3FF0
        .vectors8
        .org $FFFC
reset:
        .dw loop
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x00, 0x85, 0x04, 0xA9, 0xC0, 0x85, 0x05, 0x6C, 0x04, 0x00])

def test_fill():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
data:   .fill 0x100, 0x55 : .fill 0x100, %10101010
        .fillw 0x100, 0xAA55
'''
    co = assemble_string(program_string)
    assert co['code']['code'][0][1] == bytes([0x55] * 0x100 + [0b10101010] * 0x100 + [0x55, 0xAA] * 0x100)

def test_segment_change_with_acc_size():
    program_string = '''
        .segment "code", 0x4000, 0x4000, 0
        .segment "other", 0xC000, 0x4000, 0
        .a16
        .code
        .org start
main:
        lda #$1234
        .i16
        .other
foo:    ldx #$55aa
        .a8
        .code
l2:     lda #$66
        .i8
        .other
        ldy #$12
        lda #0x04
'''
    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == bytes([0xA9, 0x34, 0x12, 0xA9, 0x66])
    assert code['other']['code'][0][1] == bytes([0xA2, 0xaa, 0x55, 0xA0, 0x12, 0xA9, 0x04])

def test_fill_comment():
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
data:   .fill 0x100, 0x55 /* : .fill 0x100, %10101010
        .fillw 0x100, 0xAA55*/
'''
    co = assemble_string(program_string)
    print(co)
    assert co['code']['code'][0][1] == bytes([0x55] * 0x100)

def test_incbin():
    import tempfile
    fname = tempfile.mktemp()
    hello_world = "aspdfij3-18jr1[3oimrcxvipijijqw\x0343".encode("ascii")
    with open(fname, "wb") as fp:
        fp.write(hello_world)
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   .incbin "{}"
'''.format(fname)

    co = assemble_string(program_string)
    print(co)
    assert co['code']['code'][0][1] == bytes(hello_world)

def test_include():
    import tempfile
    fname = tempfile.mktemp()
    main = '''
        inc a
        dey
        jmp main
'''.encode("ascii")
    with open(fname, "wb") as fp:
        fp.write(main)
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   .include "{}"
'''.format(fname)

    co = assemble_string(program_string)
    print(co)
    assert co['code']['code'][0][1] == bytes([0x1A, 0x88, 0x4C, 0x00, 0xC0])

def test_include_path():
    import os
    import tempfile
    fname = tempfile.mktemp()
    main = '''
        inc a
        dey
        jmp main
'''.encode("ascii")
    with open(fname, "wb") as fp:
        fp.write(main)
    program_string = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   .include "{}"
'''.format(os.path.basename(fname))

    assembler = Assembler.Assembler(verbose=3, include_path=[os.path.dirname(fname)])
    co = assembler.assemble_string(program_string)
    print(co)
    assert co['code']['code'][0][1] == bytes([0x1A, 0x88, 0x4C, 0x00, 0xC0])

def test_assemble_file():
    import os
    import tempfile
    fname = tempfile.mktemp()
    main = '''
        .segment "code", 0xC000, 0x3FE0, 0
        .code
        .org start
main:   inc a
        dey
        jmp main
'''.encode("ascii")
    with open(fname, "wb") as fp:
        fp.write(main)

    assembler = Assembler.Assembler(verbose=3, include_path=[])
    co = assembler.assemble_file(fname)
    print(co)
    assert co['code']['code'][0][1] == bytes([0x1A, 0x88, 0x4C, 0x00, 0xC0])

def test_long_address():
    import os
    import tempfile
    fname = tempfile.mktemp()
    main = '''
        .segment "code", 0x02:0000, 0x10000, 0
        .code
        .org start
main:   lda data
        lda &data
        lda &data & 0xFFFF
        lda &data, x
data:   .dw 0xDEAD, 0xBEEF
'''.encode("ascii")
    with open(fname, "wb") as fp:
        fp.write(main)

    assembler = Assembler.Assembler(verbose=3, include_path=[])
    co = assembler.assemble_file(fname)
    assert co['code']['code'][0][1] == bytes([0xAD, 0x0E, 0x00, 0xAF, 0x0E, 0x00, 0x02, 0xAD, 0x0E, 0x00, 0xBF, 0x0E, 0x00, 0x02, 0xAD, 0xDE, 0xEF, 0xBE])

