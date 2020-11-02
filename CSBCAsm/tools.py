import io
import os
import pickle
import pprint
import sys
from .Lexer import CreateLexer
from .Parser import CreateParser
from .Assembler import Assembler
from . import ParserAST
from . import Opcodes
import argparse

def parse_string(s):
    if parse_string.assembler is None:
        parse_string.assembler = Assembler(verbose=3, listing_file="./test.lst")
    return parse_string.assembler.parse_string(s)
parse_string.assembler = None

def assemble_string(s):
    if parse_string.assembler is None:
        parse_string.assembler = Assembler(verbose=3, listing_file="./test.lst")
    return parse_string.assembler.assemble_string(s)

def create_memory(code_object, unused_byte=0x00):
    segments = list(code_object.keys())
    segments.sort(key=lambda s: code_object[s]['file_offset'])
    
    memory = io.BytesIO()

    last_file_offset = 0
    for segment in segments:
        cur_file_offset = code_object[segment]['file_offset']
        if cur_file_offset < 0:
            continue
    
        if last_file_offset < cur_file_offset:
            memory.write(bytes([unused_byte] * (cur_file_offset - last_file_offset)))
    
        block_offset = code_object[segment]['start']
        for code_chunk in code_object[segment]['code']: # Code pieces are already sorted
            if block_offset < code_chunk[0]:
                memory.write(bytes([unused_byte] * (code_chunk[0] - block_offset)))
                block_offset = code_chunk[0]
            memory.write(code_chunk[1])
            block_offset += len(code_chunk[1])

        last_file_offset = cur_file_offset + (block_offset - code_object[segment]['start'])
    memory.seek(0)
    return memory

def save_code_as_memory(code_object, filename, unused_byte=0x00):
    memory = create_memory(code_object, unused_byte=unused_byte)
    with open(filename, "wb") as fp:
        fp.write(memory.getbuffer())

def save_code_as_intel_hex(code_object, filename, strip=False, unused_byte=0x00):
    memory = create_memory(code_object, unused_byte=unused_byte)

    with open(filename, "wb") as fp:
        file_offset = 0
        last_high_addr = 0
        while True:
            chunk = memory.read(16)

            if len(chunk) == 0:
                fp.write(":00000001FF\n".encode("ascii"))
                break
            else:
                if not (strip and all([b == unused_byte for b in chunk])):
                    if last_high_addr != ((file_offset & 0xFFFF0000) >> 16):
                        last_high_addr = ((file_offset & 0xFFFF0000) >> 16)
                        cs = (~((0x02 + 0x00 + 0x00 + 0x04 + ((last_high_addr >> 16) & 0xFF) + (last_high_addr & 0xFF)) & 0xFF) + 1) & 0xFF
                        fp.write(":02000004{:02X}{:02X}{:02X}\n"
                                    .format((last_high_addr >> 8) & 0xFF, last_high_addr & 0xFF, cs).encode("ascii"))
                    record_type = 0x00
                    bs = [len(chunk), (file_offset >> 8) & 0xFF, file_offset & 0xFF, record_type] + list(chunk)
                    cs = (~(sum(bs) & 0xFF) + 1) & 0xFF
                    bs.append(cs)
                    fp.write(":{}\n".format("".join(["{:02X}".format(b) for b in bs])).encode("ascii"))
                file_offset += len(chunk)

def main():
    def is_dir(s):
        if os.path.isdir(s):
            return s
        raise Exception("Specified include path '{}' isn't valid".format(s))

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("input", help="the input source file")
    parser.add_argument("output", help="the output file")
    parser.add_argument("-v", "--verbose", help="increase the verbosity level (up to 3)", default=0, action="count")
    parser.add_argument("-f", "--format", help="set the output file format", choices=["pickle", "pprint", "mem", "ihex"], default="mem")
    parser.add_argument("-l", "--listing", help="set output listing file name")
    parser.add_argument("-u", "--unused", help="set the value used to fill in empty areas for memory and Intel Hex file formats", type=lambda v: int(v, 0), default=0)
    parser.add_argument("-I", "--include", help="add an include directory to the search path", action="append", type=is_dir)
    parser.add_argument("--ihex-strip", help="don't include empty lines in the ihex format (an empty line is one with all values equal to the unused value)", action="store_true")
    parser.add_argument("--version", help="display version information", action="store_true")
    args = parser.parse_args()

    if args.version:
        print("CSBCAsm version 0.1.0-beta")

    if args.unused < 0 or args.unused > 255:
        raise Exception("Invalid argument to -u/--unused: {}. Value must be 0 to 255 (0xFF).".format(args.unused))

    assembler = Assembler(verbose=args.verbose,
                          include_path=args.include,
                          listing_file=args.listing)

    if args.verbose > 0:
        print("Parsing input file {}".format(args.input))
    result = assembler.assemble_file(args.input)

    if args.format == "pickle":
        pickle.dump(result, open(args.output, "wb"))
    elif args.format == "pprint":
        with open(args.output, "w") as fp:
            fp.write(pprint.pformat(result))
    elif args.format == "mem":
        save_code_as_memory(result, args.output, unused_byte=args.unused)
    elif args.format == "ihex":
        save_code_as_intel_hex(result, args.output, args.ihex_strip, unused_byte=args.unused)

    if args.verbose > 0:
        print("Output saved to {}".format(args.output))

def AsciiToPetscii(sbytes):
    raise FeatureNotImplementedError("Currently don't know where to get or information to make a proper conversion map")
    #return list(map(lambda b: table[b], sbytes))

