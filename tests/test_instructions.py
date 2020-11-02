import pytest

from CSBCAsm import Assembler
from CSBCAsm import Lexer
from CSBCAsm import Parser
from CSBCAsm import ParserAST
from CSBCAsm.tools import parse_string, assemble_string

all_mode_instruction_sets = sum([
    list(filter(lambda it: it is not None, [
        ("{}_implied"                          .format(inst), "{}"                      .format(inst), bytes([opcodes[0]]))                       if opcodes[0]  is not None else None,
        ("{}_accumulator"                      .format(inst), "{}"                      .format(inst), bytes([opcodes[1]]))                       if opcodes[1]  is not None else None,
        ("{}_accumulator2"                     .format(inst), "{} a"                    .format(inst), bytes([opcodes[1]]))                       if opcodes[1]  is not None else None,
        ("{}_immediate"                        .format(inst), "{} #0xef"                .format(inst), bytes([opcodes[2] , 0xEF]))                if opcodes[2]  is not None else None,
        ("{}_immediate_long"                   .format(inst), ".a16 : .i16 : {} #0x42ef".format(inst), bytes([opcodes[3] , 0xEF, 0x42]))          if opcodes[3]  is not None else None,
        ("{}_absolute"                         .format(inst), "{} 0b1111_0000_1010_0101".format(inst), bytes([opcodes[4] , 0xA5, 0xF0]))          if opcodes[4]  is not None else None,
        ("{}_absolute_indirect"                .format(inst), "{} (0x1000+0x234)"       .format(inst), bytes([opcodes[5] , 0x34, 0x12]))          if opcodes[5]  is not None else None,
        ("{}_absolute_indirect_long"           .format(inst), "{} [0x1000+0x234]"       .format(inst), bytes([opcodes[6] , 0x34, 0x12]))          if opcodes[6]  is not None else None,
        ("{}_absolute_long"                    .format(inst), "{} $013412"              .format(inst), bytes([opcodes[7] , 0x12, 0x34, 0x01]))    if opcodes[7]  is not None else None,
        ("{}_direct"                           .format(inst), "{} $ef"                  .format(inst), bytes([opcodes[8] , 0xEF]))                if opcodes[8]  is not None else None,
        ("{}_direct_indirect"                  .format(inst), "{} ($ef)"                .format(inst), bytes([opcodes[9] , 0xEF]))                if opcodes[9]  is not None else None,
        ("{}_direct_indirect_long"             .format(inst), "{} [$c3]"                .format(inst), bytes([opcodes[10] , 0xc3]))               if opcodes[10] is not None else None,
        ("{}_absolute_indexed_x"               .format(inst), "{} $1024,x"              .format(inst), bytes([opcodes[11], 0x24, 0x10]))          if opcodes[11] is not None else None,
        ("{}_absolute_indexed_x_indirect"      .format(inst), "{} ($4422,x)"            .format(inst), bytes([opcodes[12], 0x22, 0x44]))          if opcodes[12] is not None else None,
        ("{}_absolute_long_indexed_x"          .format(inst), "{} $0e:1024,x"           .format(inst), bytes([opcodes[13], 0x24, 0x10, 0x0e]))    if opcodes[13] is not None else None,
        ("{}_absolute_indexed_y"               .format(inst), "{} $2410,y"              .format(inst), bytes([opcodes[14], 0x10, 0x24]))          if opcodes[14] is not None else None,
        ("{}_direct_indexed_x"                 .format(inst), "{} $15,x"                .format(inst), bytes([opcodes[15], 0x15]))                if opcodes[15] is not None else None,
        ("{}_direct_indexed_y"                 .format(inst), "{} $16,y"                .format(inst), bytes([opcodes[16], 0x16]))                if opcodes[16] is not None else None,
        ("{}_direct_indexed_x_indirect"        .format(inst), "{} ($17,x)"              .format(inst), bytes([opcodes[17], 0x17]))                if opcodes[17] is not None else None,
        ("{}_direct_indirect_indexed_y"        .format(inst), "{} ($18),y"              .format(inst), bytes([opcodes[18], 0x18]))                if opcodes[18] is not None else None,
        ("{}_direct_indirect_long_indexed_y"   .format(inst), "{} [$19],y"              .format(inst), bytes([opcodes[19], 0x19]))                if opcodes[19] is not None else None,
        ("{}_stack_relative"                   .format(inst), "{} $02,s"                .format(inst), bytes([opcodes[20], 0x02]))                if opcodes[20] is not None else None,
        ("{}_stack_relative_indirect_indexed_y".format(inst), "{} ($03,s),y"            .format(inst), bytes([opcodes[21], 0x03]))                if opcodes[21] is not None else None,
    ])) for inst, opcodes in [
                # imp   A     #     #l    a    (a)   [a]   al     dp   (dp)  [dp]  a,X   (a,X) al,X, a,Y   dp,X  dp,Y (dp,X)(dp),Y[dp],Y  sr   (sr,S),Y
        ("adc", [None, None, 0x69, 0x69, 0x6D, None, None, 0x6F, 0x65, 0x72, 0x67, 0x7D, None, 0x7F, 0x79, 0x75, None, 0x61, 0x71, 0x77, 0x63, 0x73]),
        ("and", [None, None, 0x29, 0x29, 0x2D, None, None, 0x2F, 0x25, 0x32, 0x27, 0x3D, None, 0x3F, 0x39, 0x35, None, 0x21, 0x31, 0x37, 0x23, 0x33]),
        ("cmp", [None, None, 0xC9, 0xC9, 0xCD, None, None, 0xCF, 0xC5, 0xD2, 0xC7, 0xDD, None, 0xDF, 0xD9, 0xD5, None, 0xC1, 0xD1, 0xD7, 0xC3, 0xD3]),
        ("eor", [None, None, 0x49, 0x49, 0x4D, None, None, 0x4F, 0x45, 0x52, 0x47, 0x5D, None, 0x5F, 0x59, 0x55, None, 0x41, 0x51, 0x57, 0x43, 0x53]),
        ("lda", [None, None, 0xA9, 0xA9, 0xAD, None, None, 0xAF, 0xA5, 0xB2, 0xA7, 0xBD, None, 0xBF, 0xB9, 0xB5, None, 0xA1, 0xB1, 0xB7, 0xA3, 0xB3]),
        ("ora", [None, None, 0x09, 0x09, 0x0D, None, None, 0x0F, 0x05, 0x12, 0x07, 0x1D, None, 0x1F, 0x19, 0x15, None, 0x01, 0x11, 0x17, 0x03, 0x13]),
        ("sbc", [None, None, 0xE9, 0xE9, 0xED, None, None, 0xEF, 0xE5, 0xF2, 0xE7, 0xFD, None, 0xFF, 0xF9, 0xF5, None, 0xE1, 0xF1, 0xF7, 0xE3, 0xF3]),
        ("sta", [None, None, None, None, 0x8D, None, None, 0x8F, 0x85, 0x92, 0x87, 0x9D, None, 0x9F, 0x99, 0x95, None, 0x81, 0x91, 0x97, 0x83, 0x93]),
                                         
        ("asl", [None, 0x0A, None, None, 0x0E, None, None, None, 0x06, None, None, 0x1E, None, None, None, 0x16, None, None, None, None, None, None]),
        ("dec", [None, 0x3A, None, None, 0xCE, None, None, None, 0xC6, None, None, 0xDE, None, None, None, 0xD6, None, None, None, None, None, None]),
        ("inc", [None, 0x1A, None, None, 0xEE, None, None, None, 0xE6, None, None, 0xFE, None, None, None, 0xF6, None, None, None, None, None, None]),
        ("lsr", [None, 0x4A, None, None, 0x4E, None, None, None, 0x46, None, None, 0x5E, None, None, None, 0x56, None, None, None, None, None, None]),
        ("rol", [None, 0x2A, None, None, 0x2E, None, None, None, 0x26, None, None, 0x3E, None, None, None, 0x36, None, None, None, None, None, None]),
        ("ror", [None, 0x6A, None, None, 0x6E, None, None, None, 0x66, None, None, 0x7E, None, None, None, 0x76, None, None, None, None, None, None]),
        ("stz", [None, None, None, None, 0x9C, None, None, None, 0x64, None, None, 0x9E, None, None, None, 0x74, None, None, None, None, None, None]),
                                         
        ("bit", [None, None, 0x89, 0x89, 0x2C, None, None, None, 0x24, None, None, 0x3C, None, None, None, 0x34, None, None, None, None, None, None]),
                                         
        ("ldx", [None, None, 0xA2, 0xA2, 0xAE, None, None, None, 0xA6, None, None, None, None, None, 0xBE, None, 0xB6, None, None, None, None, None]),
        ("ldy", [None, None, 0xA0, 0xA0, 0xAC, None, None, None, 0xA4, None, None, 0xBC, None, None, None, 0xB4, None, None, None, None, None, None]),
                                         
        ("cpx", [None, None, 0xE0, 0xE0, 0xEC, None, None, None, 0xE4, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("cpy", [None, None, 0xC0, 0xC0, 0xCC, None, None, None, 0xC4, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("trb", [None, None, None, None, 0x1C, None, None, None, 0x14, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tsb", [None, None, None, None, 0x0C, None, None, None, 0x04, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("stx", [None, None, None, None, 0x8E, None, None, None, 0x86, None, None, None, None, None, None, None, 0x96, None, None, None, None, None]),
        ("sty", [None, None, None, None, 0x8C, None, None, None, 0x84, None, None, None, None, None, None, 0x94, None, None, None, None, None, None]),
                                         
        ("dex", [0xCA, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("dey", [0x88, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("inx", [0xE8, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("iny", [0xC8, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("jmp", [None, None, None, None, 0x4C, 0x6C, 0xDC, 0x5C, None, None, None, None, 0x7C, None, None, None, None, None, None, None, None, None]),
        ("jml", [None, None, None, None, None, None, 0xDC, 0x5C, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("jsr", [None, None, None, None, 0x20, None, None, None, None, None, None, None, 0xFC, None, None, None, None, None, None, None, None, None]),
        ("jsl", [None, None, None, None, None, None, None, 0x22, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("nop", [0xEA, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("tax", [0xAA, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tay", [0xA8, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tcd", [0x5B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tcs", [0x1B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tdc", [0x7B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tsc", [0x3B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tsx", [0xBA, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("txa", [0x8A, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("txs", [0x9A, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("txy", [0x9B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tya", [0x98, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("tyx", [0xBB, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("pea", [None, None, None, None, 0xF4, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("pei", [None, None, None, None, None, None, None, None, None, 0xD4, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("pha", [0x48, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("phb", [0x8B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("phd", [0x0B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("phk", [0x4B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("php", [0x08, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("phx", [0xDA, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("phy", [0x5A, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("pla", [0x68, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("plb", [0xAB, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("pld", [0x2B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("plp", [0x28, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("plx", [0xFA, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("ply", [0x7A, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("clc", [0x18, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("cli", [0x58, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("cld", [0xD8, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("clv", [0xB8, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("sec", [0x38, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("sei", [0x78, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("sed", [0xF8, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("rti", [0x40, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("rts", [0x60, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("rtl", [0x6B, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("rep", [None, None, 0xC2, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("sep", [None, None, 0xE2, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("xba", [0xEB, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("xce", [0xFB, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("stp", [0xDB, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("wai", [0xCB, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("wdm", [0x42, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
                                         
        ("brk", [None, None, 0x00, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),
        ("cop", [None, None, 0x02, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]),

                # imp   A     #     a    (a)   [a]   al     dp   (dp)  [dp]  a,X   (a,X) al,X, a,Y   dp,X  dp,Y (dp,X)(dp),Y[dp],Y  sr   (sr,S),Y
    ] 
], [])

@pytest.mark.parametrize("name, inst, result", [
    ("brk_stack"  , "brk", bytes([0x00, 0x00])),
    ("cop_stack"  , "cop", bytes([0x02, 0x00])),

    ("bcc_relative", "\n_init: bcc _init", bytes([0x90, 0xFE])),
    ("bcs_relative", "\n_init: bcs _init", bytes([0xB0, 0xFE])),
    ("beq_relative", "\n_init: beq _init", bytes([0xF0, 0xFE])),
    ("bne_relative", "\n_init: bne _init", bytes([0xD0, 0xFE])),
    ("bmi_relative", "\n_init: bmi _init", bytes([0x30, 0xFE])),
    ("bpl_relative", "\n_init: bpl _init", bytes([0x10, 0xFE])),
    ("bvc_relative", "\n_init: bvc _init", bytes([0x50, 0xFE])),
    ("bvs_relative", "\n_init: bvs _init", bytes([0x70, 0xFE])),
    ("bra_relative", "\n_init: bra _init", bytes([0x80, 0xFE])),
    ("brl_relative_long", "\n_init: brl _init", bytes([0x82, 0xFD, 0xFF])),
    ("per_relative_long", "\n_init: per _init", bytes([0x62, 0xFD, 0xFF])),
    ("per_relative_long2", "\tper _next : nop\n_next: inc a", bytes([0x62, 0x01, 0x00, 0xEA, 0x1A])),

    ("mvn_block", "mvn #$14, #15", bytes([0x54, 15, 0x14])),
    ("mvp_block", "mvp #$0e, #9", bytes([0x44, 9, 0x0e])),

] + all_mode_instruction_sets)
def test_instruction(name, inst, result):
    program_string = '''
        .segment "code", 0xC000, 04000, 0
        .code
        .org start
        {}
'''.format(inst)

    code = assemble_string(program_string)
    assert code['code']['code'][0][1] == result

