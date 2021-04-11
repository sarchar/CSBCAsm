
# CSBCAsm v0.1.0-beta

CSBCAsm is an assembler specifically targeted at the 65C816 processor. While the primary target was the 65C816 processor, it should be fully compatible with the 65C02 and 65C802, provided the programmer uses the appropriate instructions.  

# Goal
The primary goal of this project is to provide a more cross-platform, modern approach to assembly on the 65C816.  Most other projects out there are either closed source, not cross-platform (or if they are, they are difficult to compile), old or lacking in features, only provided in binary form, or not free.  CSBCAsm is written in 100% open-source Python code, making it easy to install, test, and modify.

# Features

The long term goal with this project is to be a feature rich assembler.  This project is only about 3 weeks old and currently features:

* Structured statements such as IF/ELSE, CASE, DO/WHILE loops, and others.
* Macros with variable argument support
* Full 65C816 instruction set
* Hundreds of test cases, and while not yet at 100% coverage, they provide significant assurance that code is (mostly) correct.
* Cross-platform
* "Segment" support, making programming for banks outside of bank 0 more convenient.
* And more

## Installation

```
git clone https://github.com/sarchar/CSBCAsm
cd CSBCAsm && python setup.py install
```
After installation, `csbcasm` should be in your Python scripts directory.

## Usage

```
usage: csbcasm [-h] [-v] [-f {pickle,pprint,mem,ihex}] [-l LISTING]
               [-u UNUSED] [-I INCLUDE] [--ihex-strip] [--version]
               input output

positional arguments:
  input                 the input source file
  output                the output file

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase the verbosity level (up to 3) (default: 0)
  -f {pickle,pprint,mem,ihex}, --format {pickle,pprint,mem,ihex}
                        set the output file format (default: mem)
  -l LISTING, --listing LISTING
                        set output listing file name (default: None)
  -u UNUSED, --unused UNUSED
                        set the value used to fill in empty areas for memory
                        and Intel Hex file formats (default: 0)
  -I INCLUDE, --include INCLUDE
                        add an include directory to the search path (default:
                        None)
  --ihex-strip          don't include empty lines in the ihex format (an empty
                        line is one with all values equal to the unused value)
                        (default: False)
  --version             display version information (default: False)
```

CSBCAsm takes as input only a single source file and produces a single output file. If you have a project, like most, that contain multiple files, you will need to wrap them all in a master file using `.include` statements.

Output file types include `pickle`, Python's pickle module, which will save a dictionary representing the code to be produced after assembling.  If you would like to see the dictionary, you can use the output file type `pprint`, which will save the output in a prettier format.

Output file type `mem` will be a flat memory output of your program, and `ihex` will be the Intel HEX representation of that same memory.  You can use `--ihex-strip` to remove lines containing all 0's, or if you want to change the empty/unused space character, specify `-u` with an argument, such as `0xFF`.

## Syntax

### Instructions and Addressing Modes

There is very little to say here. CSBCAsm aims to be fairly identical to most other assemblers with regards to instruction names and addressing mode syntax.  There are only a few minutiae to discuss, but otherwise the syntax you are familiar with should work.  Examples include,

```
	LDA [0x01], Y   ; Direct page long indirect indexed Y
	STA 0x05, S     ; Stack relative
	CMP $04:1234, X ; Absolute long indexed X
```

Statements cannot begin in column 0.

### Expressions

#### Operators

CSBCAsm includes support for

* Logical OR `||`, AND `&&`, and NOT `!`
* Comparison Equal to `==`, not equal to `!=`, and comparisons `<`, `<=` , `>`, `>=`
* Binary operators AND `&`, OR `|`, NOT `~`,  XOR `^`, LSHIFT `<<`, RSHIFT `>>`
* High and low byte from word unary operators `>` and `<` (respectively).  Long word support using `&` (see below).
* addition `-`, subtraction `-`
* multiplication `*`, division `/`, modulo `%`, power `**`
* And parentheses `()` to group expressions

#### Labels, names, equates

Equates require a name, an equal sign (=) and an expression.	Examples,

```
	STACK_PTR = 0x1FF
	MEMORY = 0x2000
	MEMORY_SIZE = 0x1000
	MEMORY_END = MEMORY + MEMORY_SIZE
```

Labels require the use of a colon (:) and must start in column 0:

```
main:
	jmp main
```

Instructions can be on the same line as the label.

A **name** is a generic term for either a **label** or an **equate**.  **Equates** cannot reference labels, but expressions can reference both labels and equates.

All **name**s are case-sensitive.  It may be the case that this changes in the future, since I believe most assemblers are case-insensitive.  

No **name** can start with a period (.), or be the same as CPU register.

Normally, labels aren't referenceable outside of the segment they're defined in. If you want to reference a label, you must mark it using the `.global` compiler directive.

### Temporary labels

Diverging from most other assemblers, temporary labels are prefixed with a **@** sign.  When there is an ambiguity using a temporary label, you must use either a plus (+) or minus (-) following the label to indicate which label you intend to reference. Example,

```
@1:
	<do stuff>
	bne @1+
	<other stuff>
	bra @1-
@1: jmp @1
```

Notice that the final JMP doesn't require the minus sign, as there's no ambiguity on which label its referencing -- it uses the most recent definition.  It's suggested to always use + and - when using temporary labels, however.

### This label

The local this label `.` can be used to refer to the address of the current instruction.

### Long Labels

Labels are always taken to be 2 bytes unless specified with the long label operator `&`.  Example:

```
	LDA &data, X
	<...>
data:
	<...>
```

This is the only way to differentiate Absolute Indexed X and Absolute Long Indexed X modes.  The above instruction will be 4 bytes long and use opcode 0xBF.

### Quoted Strings

The assembler understands quoted strings in only a few circumstances -- namely, with the use of the `.DB` compiler directive.  Escape sequences are currently not implemented (TODO).  Example,
```
hello_word:
	.db "Hello, world!", 0
```

## Compiler Directives

All compiler directives begin with a period `.`.  Compiler directives are case-insensitive.  The following directives are currently implemented:

* `.A8`, `.A16` tell the assembler that the following code is in accumulator/memory normal/long mode. That is, immediate mode instructions that reference the accumulator are 2 or 3 bytes.
* `.I8`, `.I16` tell the assembler that the following code is in index normal/long mode. That  is, immediate mode instructions that reference the index registers are 2 or 3 bytes.
* `.IF <expression>`, `.ELIF <expression>`, `.ELSE`, `.ENDIF` Assemble-time IF/ELSE statement.  Equates are allowed in the expression, labels are not. Example
	```
	.if DEBUG
		lda #0x01
	.else
		lda #0x00
	.endif
	```
    **NOTE**: In IF/ELIF statements *only*, undefined labels are evaluated to $00.
* `.DB <list of expressions>` Declare Bytes.  The argument is a comma separated list of expressions. Or just byte values.  Quoted strings are accepted.
* `.DW <list of expressions>` Declare Words.  The argument is a comma separated list of expressions. Or just words.  Quoted strings are NOT accepted.
* `.FILL <count-expression>, <fill value-expression>` Fill with a repeating byte value.
* `.FILLW <count-expression>, <fill value-expression>` Fill with a repeating word value.
* `.GLOBAL <label>` Set a **label** as global.  Otherwise, labels aren't useable outside of their segment.
* `.INCLUDE <quoted string>` Directly include a source file at this location.
* `.INCBIN <quoted string>` Directly include a binary file at this location.
* `.SEGMENT <name-quoted string>, <base address-expression>, <size-expression>, <file offset-expression>`  Define a segment named *name* starting at address `base address` in memory of size `size`.  `file offset` can be a positive number indicating the starting location in the output file or `-1` indicating not to include the segment in the output file.
* `.<name>`  Switch to segment previously defined. Exmaple:
	```
		.segment "code", 0x8000, 0x8000, 0
		.code
	```
* `.MACRO / .ENDMACRO` Define a macro (see below).
* `.VALOOP / .ENDVALOOP` Variable argument loop only useable in macros (see below).

## Macros

CSBCAsm has preliminary support for macros.  To define a macro, you must declare a label on the same line as the `.MACRO` compiler directive:

```
INDEX16: .MACRO
		REP %00010000
		.I16
		.ENDMACRO
```

To call a macro, simply use it as if it were an instruction.

```
main:
	INDEX16
	JMP main
```

To call a macro with arguments, just include them as if they were operands.

```
main:
	MYMACRO $00, $01, $02
	JMP main
```

A macro can take any number of named parameters followed by the optional variable-argument syntax `...`.

```
ONLY5: .MACRO one, two, ...
		INC one
		DEC two
		.IF \L == 3
			LDA #$15
		.ENDIF
		.ENDMACRO
```

where `\L` will be replaced with the length of the variable arguments list, not including the named arguments.  

You can loop over the variable arguments using `.VALOOP` and `.ENDVALOOP`:

```
SETV:	.MACRO ...
		.VALOOP
			LDA \v
			LDX #\i
			STA (0x00), X
		.ENDVALOOP
```

The escape values `\i` and `\v` will be replaced with the index and the actual value of the variable arguments list, respectively, throughout the loop.

## Structured Statements

CSBCAsm supports various structed assembly statements. The goal is to help write clearer code while still maintaining the ability to translate statements 1-to-1 with the code that's generated.  Look at the LISTING file of your project to see the generated code.

In all the following statements that use condition codes, `condition` can be one of:

	C_SET, C_CLEAR, N_SET, N_CLEAR, V_SET, V_CLEAR, Z_SET, Z_CLEAR

representing the processor states `C` (carry), `N` (negative), `V` (overflow), and `Z` (zero).
	
### IF/ELSE/ENDIF

`IF <condition>`
	`...`
`ENDIF`

Example:

```
main:  
        lda $00
        if z_clear
            sta $01
        else
            inc $00
        endif
```

Generates:

```
00:C000 A5 00                  LDA 0x00
00:C002 F0 04                  BEQ 0xC008
00:C004 85 01                  STA 0x01
00:C006 80 02                  BRA 0xC00A
00:C008 E6 00                  INC 0x00
```

### DO/UNTIL

`DO`
	`...`
`UNTIL <condition>`

Example:

```
main: 	do
			do
				dex
			until n_set
			dey
		until z_set
```

Will generate the following code:

```
00:C000 CA                     DEX 
00:C001 10 FD                  BPL 0xC000
00:C003 88                     DEY 
00:C004 D0 FA                  BNE 0xC000
```

### DO/FOREVER

`DO`
	`...`
`FOREVER`

Example:

```
main: 	do
			inc $00
		forever
```

Generates:

```
00:C000 E6 00                  INC 0x00
00:C002 80 FC                  BRA 0xC000
```
			
* Note: BRL will be used when the branch is required

### WHILE/ENDWHILE

`WHILE <condition>`
	`...`
`ENDWHILE`

Example:

```
main:  
        lda $00
        while z_clear
            inc $01
            lda $00
        endwhile
```

Generates:

```
00:C000 A5 00                  LDA 0x00
00:C002 F0 06                  BEQ 0xC00A
00:C004 E6 01                  INC 0x01
00:C006 A5 00                  LDA 0x00
00:C008 D0 FA                  BNE 0xC004
```


### SWITCH/CASE/ENDSWITCH

With SWITCH statements, you can use `switch a` to test the A register, or `switch x` / `switch y` for the index registers.

`SWITCH <a/x/y>`
`CASE #imm`
	`...`
`CASE #imm2`
	`...`
`ENDWHILE`

Currently only immediate values are supported for CASE statements.

Example:

```
main:  
        ldy $00
        switch y
        case #0x00
            iny
        case #0x01
            dey
        endswitch
```

Will generate:

```
00:C000 A4 00                  LDY 0x00
00:C002 C0 00                  CPY 0x00
00:C006 C8                     INY 
00:C007 80 05                  BRA 0xC00E
00:C007 80 05 C0 01            CPY 0x01
00:C00D 88                     DEY 
```

## Contact

If you would like to contact me, E-mail me at <chuck+csbcasm@borboggle.com>

If you find a bug, please submit a bug report.

And my apologies for any badly written code, of which I'm sure there's plenty.


