import enum

# Some info from https://undisbeliever.net/snesdev/65816-opcodes.html#rti-return-from-interrupt
# Other info from WDC's W65C816S datasheet

class OpcodeDatabase():
    OI_OPCODE = 0
    OI_SIZE   = 1
    OI_CYCLES = 2
    OI_FLAGS  = 3

    IF_EXTRA_BYTE16                      = 1 << 0   # Add 1 byte for Native mode
    IF_EXTRA_CYCLE16                     = 1 << 1   # Add 1 cycle if Native mode
    IF_EXTRA_CYCLE_DL_NONZERO            = 1 << 2   # Add 1 cycle for direct register low (DL) not equal to 0
    IF_EXTRA_CYCLE_BRANCH_TAKEN          = 1 << 3
    IF_EXTRA_CYCLE_BRANCH_OVER_PAGE_IN_E = 1 << 4
    IF_EXTRA_2_CYCLE16                   = 1 << 5   # Add 2 cycles if Native mode
    IF_EXTRA_ACCUMULATOR_IMMEDIATE       = 1 << 6
    IF_EXTRA_INDEX_IMMEDIATE             = 1 << 7
 
    class AddressingMode(enum.Enum):
        IMPLIED = 0
        ACCUMULATOR = 1 # Separate from IMPLIED so the programmer can use 'ASL A' too
        IMMEDIATE = 2
        RELATIVE = 3
        RELATIVE_LONG = 4
        DIRECT = 5
        DIRECT_INDEXED_X = 6
        DIRECT_INDEXED_Y = 7
        DIRECT_INDIRECT = 8
        DIRECT_INDEXED_X_INDIRECT = 9
        DIRECT_INDIRECT_INDEXED_Y = 10
        DIRECT_INDIRECT_LONG = 11
        DIRECT_INDIRECT_LONG_INDEXED_Y = 12
        ABSOLUTE = 13
        ABSOLUTE_INDEXED_X = 14
        ABSOLUTE_INDEXED_Y = 15
        ABSOLUTE_LONG = 16
        ABSOLUTE_LONG_INDEXED_X = 17
        ABSOLUTE_INDIRECT = 18
        ABSOLUTE_INDIRECT_LONG = 19
        ABSOLUTE_INDEXED_X_INDIRECT = 20
        STACK = 21
        STACK_RELATIVE = 22
        STACK_RELATIVE_INDIRECT_INDEXED_Y = 23
        BLOCK_MOVE = 24
        BRKCOP = 25
       
    def __init__(self):
        self.opcodes = {                               
            'ADC': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0x69),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x65),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x75),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0x61),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0x71),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0x72),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0x67),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0x77),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x6D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x7D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0x79),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0x6F),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0x7F),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0x63),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0x73),
            },
            'AND': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0x29),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x25),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x35),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0x21),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0x31),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0x32),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0x27),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0x37),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x2D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x3D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0x39),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0x2F),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0x3F),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0x23),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0x33),
            },

            'ASL': { 
                OpcodeDatabase.AddressingMode.ACCUMULATOR                      : OpcodeDatabase._accumulator(0x0A),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x06),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x16),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x0E),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x1E),
            },


            'BCC': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0x90) },
            'BCS': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0xB0) },
            'BEQ': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0xF0) },

            'BIT': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0x89),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x24),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x34),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x2C),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x3C),
            },

            'BNE': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0xD0) },
            'BMI': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0x30) },
            'BPL': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0x10) },
            'BRA': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0x80) },
            'BRK': { 
                OpcodeDatabase.AddressingMode.BRKCOP    : OpcodeDatabase._brkcop(0x00),
                OpcodeDatabase.AddressingMode.IMMEDIATE : OpcodeDatabase._immediate(0x00),
            },
            'BRL': { OpcodeDatabase.AddressingMode.RELATIVE_LONG : OpcodeDatabase._relative_long(0x82) },
            'BVC': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0x50) },
            'BVS': { OpcodeDatabase.AddressingMode.RELATIVE : OpcodeDatabase._relative(0x70) },

            'CLC': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0x18) },
            'CLI': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0x58) },
            'CLD': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xD8) },
            'CLV': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xB8) },

            'CMP': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0xC9),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xC5),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0xD5),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0xC1),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0xD1),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0xD2),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0xC7),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0xD7),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xCD),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0xDD),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0xD9),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0xCF),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0xDF),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0xC3),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0xD3),
            },


            'COP': { 
                OpcodeDatabase.AddressingMode.BRKCOP    : OpcodeDatabase._brkcop(0x02),
                OpcodeDatabase.AddressingMode.IMMEDIATE : OpcodeDatabase._immediate(0x02),
            },

            'CPX': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_index(0xE0),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xE4),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xEC),
            },

            'CPY': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_index(0xC0),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xC4),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xCC),
            },


            'DEC': { 
                OpcodeDatabase.AddressingMode.ACCUMULATOR                      : OpcodeDatabase._accumulator(0x3A),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xC6),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0xD6),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xCE),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0xDE),
            },

            "DEX": {
                OpcodeDatabase.AddressingMode.IMPLIED                        : OpcodeDatabase._implied(0xCA),
            },
            "DEY": {
                OpcodeDatabase.AddressingMode.IMPLIED                        : OpcodeDatabase._implied(0x88),
            },


            'EOR': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0x49),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x45),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x55),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0x41),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0x51),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0x52),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0x47),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0x57),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x4D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x5D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0x59),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0x4F),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0x5F),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0x43),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0x53),
            },

            'INC': {
                OpcodeDatabase.AddressingMode.ACCUMULATOR                      : OpcodeDatabase._accumulator(0x1A),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xE6),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0xF6),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xEE),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0xFE),
            },

            'INX': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xE8) },
            'INY': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xC8) },

            'JML': { # another name for JMP
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT_LONG      : OpcodeDatabase._absolute_indirect_long(0xDC),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG               : OpcodeDatabase._absolute_long(0x5C),
            },
            'JMP': {
                OpcodeDatabase.AddressingMode.ABSOLUTE                    : OpcodeDatabase._absolute(0x4C),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT           : OpcodeDatabase._absolute_indirect(0x6C),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT_LONG      : OpcodeDatabase._absolute_indirect_long(0xDC),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X_INDIRECT : OpcodeDatabase._absolute_indexed_x_indirect(0x7C),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG               : OpcodeDatabase._absolute_long(0x5C),
            },
            'JSL': {
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG : OpcodeDatabase._absolute_long(0x22),
            },
            'JSR': {
                OpcodeDatabase.AddressingMode.ABSOLUTE : OpcodeDatabase._absolute(0x20),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X_INDIRECT : OpcodeDatabase._absolute_indexed_x_indirect(0xFC),
            },

            'LDA': {
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0xA9),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xA5),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0xB4),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0xA1),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0xB1),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0xB2),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0xA7),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0xB7),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xAD),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0xBD),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0xB9),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0xAF),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0xBF),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0xA3),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0xB3),
            },

            'LDX': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_index(0xA2),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xA6),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_Y                 : OpcodeDatabase._direct_indexed_y(0xB6),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xAE),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0xBE),
            },

            'LDY': { 
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_index(0xA0),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xA4),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0xB4),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xAC),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0xBC),
            },

            'LSR': {
                OpcodeDatabase.AddressingMode.ACCUMULATOR                      : OpcodeDatabase._accumulator(0x4A),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x46),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x56),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x4E),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x5E),
            },


            'MVN': {
                OpcodeDatabase.AddressingMode.BLOCK_MOVE : OpcodeDatabase._block_move(0x54)
            },

            'MVP': {
                OpcodeDatabase.AddressingMode.BLOCK_MOVE : OpcodeDatabase._block_move(0x44)
            },

            'NOP': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xEA) },

            'ORA': {
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0x09),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x05),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x15),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0x01),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0x11),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0x12),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0x07),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0x17),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x0D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x1D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0x19),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0x0F),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0x1F),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0x03),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0x13),
            },

            'PEA': { OpcodeDatabase.AddressingMode.ABSOLUTE        : OpcodeDatabase._absolute(0xF4) }, # Technically "Stack Absolute" mode but all the code should match
            'PEI': { OpcodeDatabase.AddressingMode.DIRECT_INDIRECT : OpcodeDatabase._direct_indirect(0xD4) }, # Technically "Stack (Direct Indirect)" mode but all the code should match
            'PER': { OpcodeDatabase.AddressingMode.RELATIVE_LONG   : OpcodeDatabase._relative_long(0x62) },

            'REP': { OpcodeDatabase.AddressingMode.IMMEDIATE: OpcodeDatabase._immediate(0xC2) },

            'PHA': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x48) },
            'PHB': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x8B) },
            'PHD': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x0B) },
            'PHK': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x4B) },
            'PHP': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x08) },
            'PHX': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0xDA) },
            'PHY': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x5A) },
            'PLA': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x68) },
            'PLB': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0xAB) },
            'PLD': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x2B) },
            'PLP': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x28) },
            'PLX': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0xFA) },
            'PLY': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x7A) },

            'ROL': {
                OpcodeDatabase.AddressingMode.ACCUMULATOR                      : OpcodeDatabase._accumulator(0x2A),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x26),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x36),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x2E),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x3E),
            },
            
            'ROR': {
                OpcodeDatabase.AddressingMode.ACCUMULATOR                      : OpcodeDatabase._accumulator(0x6A),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x66),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x76),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x6E),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x7E),
            },


            'RTI': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x40) },
            'RTL': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x6B) },
            'RTS': { OpcodeDatabase.AddressingMode.STACK : OpcodeDatabase._stack(0x60) },

            'SBC': {
                OpcodeDatabase.AddressingMode.IMMEDIATE                        : OpcodeDatabase._immediate_accumulator(0xE9),
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0xE5),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0xF5),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0xE1),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0xF1),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0xF2),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0xE7),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0xF7),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0xED),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0xFD),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0xF9),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0xEF),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0xFF),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0xE3),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0xF3),
            },

            'SEC': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0x38) },
            'SED': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xF8) },
            'SEI': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0x78) },
            'SEP': { OpcodeDatabase.AddressingMode.IMMEDIATE: OpcodeDatabase._immediate(0xE2) },
            'STA': {
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x85),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x95),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : OpcodeDatabase._direct_indexed_x_indirect(0x81),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : OpcodeDatabase._direct_indirect_indexed_y(0x91),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : OpcodeDatabase._direct_indirect(0x92),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : OpcodeDatabase._direct_indirect_long(0x87),
                OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : OpcodeDatabase._direct_indirect_long_indexed_y(0x97),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x8D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x9D),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : OpcodeDatabase._absolute_indexed_y(0x99),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : OpcodeDatabase._absolute_long(0x8F),
                OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : OpcodeDatabase._absolute_long_indexed_x(0x9F),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : OpcodeDatabase._stack_relative(0x83),
                OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: OpcodeDatabase._stack_relative_indirect_indexed_y(0x93),
            },

            'STP': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xDB) },

            'STX': { 
                OpcodeDatabase.AddressingMode.ABSOLUTE                     : OpcodeDatabase._absolute(0x8E),
                OpcodeDatabase.AddressingMode.DIRECT                       : OpcodeDatabase._direct(0x86),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_Y             : OpcodeDatabase._direct_indexed_y(0x96),
            },

            'STY': { 
                OpcodeDatabase.AddressingMode.ABSOLUTE                     : OpcodeDatabase._absolute(0x8C),
                OpcodeDatabase.AddressingMode.DIRECT                       : OpcodeDatabase._direct(0x84),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X             : OpcodeDatabase._direct_indexed_x(0x94),
            },

            'STZ': {
                OpcodeDatabase.AddressingMode.DIRECT                           : OpcodeDatabase._direct(0x64),
                OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : OpcodeDatabase._direct_indexed_x(0x74),
                OpcodeDatabase.AddressingMode.ABSOLUTE                         : OpcodeDatabase._absolute(0x9C),
                OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : OpcodeDatabase._absolute_indexed_x(0x9E),
            },


            'TAX': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0xAA) },
            'TAY': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0xA8) },
            'TCD': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x5B) },
            'TCS': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x1B) },
            'TDC': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x7B) },

            'TRB': {
                OpcodeDatabase.AddressingMode.ABSOLUTE : OpcodeDatabase._absolute(0x1C),
                OpcodeDatabase.AddressingMode.DIRECT   : OpcodeDatabase._direct(0x14),
            },

            'TSB': {
                OpcodeDatabase.AddressingMode.ABSOLUTE : OpcodeDatabase._absolute(0x0C),
                OpcodeDatabase.AddressingMode.DIRECT   : OpcodeDatabase._direct(0x04),
            },

            'TSC': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x3B) },
            'TSX': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0xBA) },
            'TXA': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x8A) },
            'TXS': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x9A) },
            'TXY': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x9B) },
            'TYA': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0x98) },
            'TYX': { OpcodeDatabase.AddressingMode.IMPLIED : OpcodeDatabase._implied(0xBB) },

            'WAI': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xCB) },
            'WDM': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0x42) }, # Don't use this.
            'XBA': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xEB) },
            'XCE': { OpcodeDatabase.AddressingMode.IMPLIED  : OpcodeDatabase._implied(0xFB) },
        }

        self.addressing_modes = {}
        for opcode, modes in self.opcodes.items():
            self.addressing_modes[opcode] = tuple(modes.keys())

    @staticmethod
    def _implied(opcode):
        return (opcode, 1, 2, 0)

    @staticmethod
    def _accumulator(opcode):
        return (opcode, 1, 2, 0)

    @staticmethod
    def _immediate(opcode):
        return (opcode, 2, 2, OpcodeDatabase.IF_EXTRA_BYTE16 
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _immediate_accumulator(opcode):
        return (opcode, 2, 2, OpcodeDatabase.IF_EXTRA_BYTE16 
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_ACCUMULATOR_IMMEDIATE)

    def _immediate_index(opcode):
        return (opcode, 2, 2, OpcodeDatabase.IF_EXTRA_BYTE16 
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_INDEX_IMMEDIATE)

    def _stack_relative(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _stack_relative_indirect_indexed_y(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _direct(opcode):
        return (opcode, 2, 3, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indexed_x(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indexed_y(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indirect(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indirect_long(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indirect_long_indexed_y(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indexed_x_indirect(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _direct_indirect_indexed_y(opcode):
        return (opcode, 2, 0, OpcodeDatabase.IF_EXTRA_BYTE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE16
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_DL_NONZERO)

    def _relative(opcode):
        return (opcode, 2, 2, OpcodeDatabase.IF_EXTRA_CYCLE_BRANCH_TAKEN
                                 | OpcodeDatabase.IF_EXTRA_CYCLE_BRANCH_OVER_PAGE_IN_E)

    def _relative_long(opcode):
        return (opcode, 3, 0, 0)

    def _absolute(opcode):
        return (opcode, 3, 0, OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _absolute_indexed_x(opcode):
        return (opcode, 3, 0, OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _absolute_indexed_y(opcode):
        return (opcode, 3, 0, OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _absolute_indexed_x_indirect(opcode):
        return (opcode, 3, 0, OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _absolute_long(opcode):
        return (opcode, 4, 0, OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _absolute_long_indexed_x(opcode):
        return (opcode, 4, 0, OpcodeDatabase.IF_EXTRA_CYCLE16)

    def _absolute_indirect(opcode):
        return (opcode, 3, 5, 0)

    def _absolute_indirect_long(opcode):
        return (opcode, 3, 6, 0)

    def _brkcop(opcode):
        # at this point i've given up on cycles; i'm never gonna use them. TODO: delete all mention of cycles
        return (opcode, 2, 0, 0)

    def _stack(opcode):
        # at this point i've given up on cycles; i'm never gonna use them. TODO: delete all mention of cycles
        return (opcode, 1, 0, 0)

    def _block_move(opcode):
        return (opcode, 3, 0, 0)

    def get_addressing_modes(self, opcode_str):
        opcode_str = opcode_str.upper()
        return self.addressing_modes.get(opcode_str, None)

    def get_instruction_flags(self, opcode_str, addressing_mode):
        modes = self.opcodes[opcode_str.upper()]
        opinfo = modes[addressing_mode]
        return opinfo[OpcodeDatabase.OI_FLAGS]

    def get_instruction_size(self, opcode_str, addressing_mode):
        modes = self.opcodes[opcode_str.upper()]
        opinfo = modes[addressing_mode]
        return opinfo[OpcodeDatabase.OI_SIZE]

    def get_instruction_opcode(self, opcode_str, addressing_mode):
        modes = self.opcodes[opcode_str.upper()]
        opinfo = modes[addressing_mode]
        return opinfo[OpcodeDatabase.OI_OPCODE]
        
