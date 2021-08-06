import copy
import io
import os

from . import ParserAST
from . import Opcodes

from .Lexer import CreateLexer
from .Parser import CreateParser, ParseError
from .Errors import *

from rply.errors import LexingError

# Hacky wrapper around LexerStream so we can
# skip over multiline comments in our single line parser
class LexerWrapper():
    def __init__(self, lexer_stream, in_multiline_comment=False):
        self.lexer_stream = lexer_stream
        self.in_multiline_comment = in_multiline_comment
        self.ended_with_comment = in_multiline_comment

    def __iter__(self):
        self.iter = self.lexer_stream.__iter__()
        return self

    def next(self):
        v = self.lexer_stream.next()
        if self.in_multiline_comment:
            if v.gettokentype() != 'MULTILINE_COMMENT_END':
                raise StopIteration
            else:
                # skip this token and keep going!
                self.in_multiline_comment = False
                self.ended_with_comment = False
                v = self.lexer_stream.next()
        if v.gettokentype() == 'MULTILINE_COMMENT_START':
            self.ended_with_comment = True
            raise StopIteration
        return v

    def __next__(self):
        return self.next()

class Assembler():
    STRUCTURED_LABELS = ("IF", "ELSE", "ENDIF", "DO", "UNTIL", "FOREVER", "WHILE", "ENDWHILE", "SWITCH", "CASE", "ENDSWITCH")
    BUILT_IN_LABELS = ("A", "X", "Y", "S", ".") + STRUCTURED_LABELS

    VERBOSE_EVERYTHING = 3
    VERBOSE_BUILD = 2
    VERBOSE_BASIC = 1
    VERBOSE_NONE = 0

    LISTING_SOURCE_COLUMN = 32
    LISTING_COMMENT_COLUMN = 52

    def __init__(self, verbose=0, include_path=[], listing_file=None):
        self.verbose = verbose
        self.include_path = include_path
        self.listing_file = listing_file
        self.segments = {}
        self.opcodes = Opcodes.OpcodeDatabase()
        self.lexer = CreateLexer()
        self.parser = CreateParser()

    def parse_string(self, s, fn="<unknown>", included_from=None):
        lines = s.split("\n")
        program = [] # list of lines
        in_multiline_comment = False
        for i, line in enumerate(lines):
            if len(line) > 0:
                if in_multiline_comment:
                    j = line.find("*/")
                    if j < 0:
                        continue
                    line = line[j:]

                tokens = LexerWrapper(self.lexer.lex(line), in_multiline_comment=in_multiline_comment)
                try:
                    parsed_line = self.parser.parse(tokens)
                except LexingError as e:
                    print("failure parsing line {} in file {}: {}".format(i + 1, fn, str(e)))
                    raise
                except ParseError as e:
                    print("failure parsing line {} in file {}: {}".format(i + 1, fn, str(e)))
                    raise
                parsed_line.line_number = i + 1
                parsed_line.filename = fn
                parsed_line.included_from = included_from
                program.append(parsed_line)
    
                in_multiline_comment = tokens.ended_with_comment
    
        return program

    def assemble_string(self, s, fn):
        return self.assemble(self.parse_string(s, fn))

    def assemble_file(self, fn):
        with open(fn, "r") as fp:
            buf = fp.read()
        return self.assemble_string(buf, fn)

    def assemble(self, program):
        pb = ProgramBuilder(self, program)

        # Parse the AST, create the segments and the builders
        pb.build_code_actions()
        if self.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Done creating build actions")

        # Run through determining the programs sizes and validity
        pb.validate_actions()

        # Determine all name references
        pb.finalize_labels()

        # Pass 3: ...
        lf = None
        if self.listing_file is not None:
            lf = open(self.listing_file, "w")
        code = pb.generate_code_object(lf)
        if lf is not None:
            lf.close()
        return code

class ProgramBuilder():
    def __init__(self, assembler, program):
        assert all(isinstance(x, ParserAST.Line) for x in program)
        self.assembler = assembler
        self.program = program
        self.current_segment = None
        self.build_address = None

        self.accumulator_mode = 8
        self.index_mode = 8 

        self.actions = []

        self._segments = {
        }

        self._segment_builders = {
        }

        self._directives = {
            'A8'       : self._process_scd_a8,
            'A16'      : self._process_scd_a16,
            'ELIF'     : self._process_scd_elif,
            'ELSE'     : self._process_scd_else,
            'ENDIF'    : self._process_scd_endif,
            'ENDVALOOP': self._process_scd_endvaloop,
            'I8'       : self._process_scd_i8,
            'I16'      : self._process_scd_i16,
            'IF'       : self._process_scd_if,
            'DB'       : self._process_scd_db,
            'DW'       : self._process_scd_dw,
            'DL'       : self._process_scd_dl,
            'FILL'     : self._process_scd_fill,
            'FILLW'    : self._process_scd_fillw,
            'GLOBAL'   : self._process_scd_global,
            'GLOBALALL': self._process_scd_globalall,
            'INCLUDE'  : self._process_scd_include,
            'INCBIN'   : self._process_scd_incbin,
            'MACRO'    : self._process_scd_macro,
            'ENDMACRO' : self._process_scd_endmacro,
            'ORG'      : self._process_scd_org,
            'SEGMENT'  : self._process_scd_segment,
            'VALOOP'   : self._process_scd_valoop,
        }

        self._label_declarations = {
        }

        self._global_labels = {
        }

        self._all_labels = set() # Only useful to prevent EQUATES from overriding local labels

        self._equates = {
        }

        self._flow_control = []

        self._macros = {
        }

        self._capturing_actions = []

        self._macro_arguments = []

    def add_segment(self, segment):
        uv = segment.name.value.upper()
        if uv in self._segments:
            raise SegmentRedefinitionError("Line {}: cannot redefine segment '{}'".format(segment.line.line_number, uv))
        self._segments[uv] = segment

    def get_segment(self, segment_name):
        return self._segments.get(segment_name.upper(), None)

    def set_current_segment(self, segment):
        self.current_segment = segment

    def require_current_segment(self, line):
        if self.current_segment is None:
            raise NoSegmentError("Line {}: statement requires segment".format(line.line_number))
        return self.current_segment

    def get_equate(self, name_str):
        return self._equates.get(name_str, None)

    def get_label(self, label_str):
        # Check segment-local labels first
        if self.current_segment is not None:
            label_declaration = self.current_segment.get_label(label_str)
            if label_declaration is not None:
                return label_declaration
        # Then check global/export labels
        return self.get_global_label(label_str)

    def get_global_label(self, label_str):
        return self._label_declarations.get(label_str, None)

    def set_global_label(self, line, label_str):
        current_segment = self.require_current_segment(line)
        self._global_labels[label_str] = { 'segment': current_segment }
        label_declaration = current_segment.get_label(label_str)
        if label_declaration is not None:
            self._label_declarations[label_str] = label_declaration

    def verify_label_available(self, label_str, line, current_segment):
        if label_str[0] == '.':
            raise ReservedNameError("Line {}: cannot declare labels or equates using a starting period ('.'): {}".format(line.line_number, label_str))

        if current_segment is not None:
            old = current_segment.get_label(label_str)
            if (label_str[0] != '@' and old is not None) or label_str in self._label_declarations:
                raise LabelRedefinitionError("Line {}: label redefined: {}".format(line.line_number, label_str))

        if label_str.upper() in Assembler.BUILT_IN_LABELS:
            raise ReservedNameError("Line {}: reserved name used as label: {}".format(line.line_number, label_str))
        
        equ = self.get_equate(label_str)
        if equ is not None:
            raise LabelRedefinitionError("Line {}: label is already assigned to an equate: {}".format(line.line_number, label_str))

        # Technically, these names might be just fine to use as labels?
        addressing_modes = self.assembler.opcodes.get_addressing_modes(label_str)
        if addressing_modes is not None:
            raise ReservedNameError("Line {}: instruction name used as label: {}".format(line.line_number, label_str))

        if label_str in self._macros:
            raise LabelRedefinitionError("Line {}: label is already assigned to a macro: {}".format(line.line_number, label_str))

    def declare_label_here(self, label_str, line):
        current_segment = self.require_current_segment(line)
        
        self._all_labels.add(label_str)

        if label_str[0] == '@':
            if label_str[-1] == '+':
                label_str = label_str[:-1]
            if label_str[-1] == '-':
                label_str = label_str[:-1]
            old = current_segment.get_label(label_str)
            if old is not None:
                label_declaration = old
                label_declaration['build_addresses'].append(self.build_address.collapse())
                label_declaration['build_addresses'].sort(key=lambda v: v.eval())
                return label_declaration

        self.verify_label_available(label_str, line, current_segment)

        label_declaration = {
            'segment': current_segment,
            'build_addresses': [self.build_address.collapse()],
            'line': line
        }

        current_segment.declare_label(label_str, label_declaration)

        if (label_str in self._global_labels and self._global_labels[label_str]['segment'] is current_segment) or current_segment.global_all:
            if label_str == 'MATH_AddYA_16':
                included_from_files = []
                k = line.included_from
                while k is not None:
                    if isinstance(k.filename, ParserAST.QuotedString):
                        included_from_files.append(k.filename.value)
                    else:
                        included_from_files.append(k.filename)
                    k = k.included_from
                included_from = ', which was included from '.join(included_from_files)
                print(label_str, 'defined global at line', line.line_number, "file", line.filename.value, 'included from', included_from)
            self._label_declarations[label_str] = label_declaration
            
        return label_declaration

    def make_label_references(self, line, expr, action):
        self.require_current_segment(line).make_label_references(line, expr, action, self.build_address)

    def replace_equates(self, line, operand, replace_undefined=None):
        search_results = operand.find_referenced_names()
        if search_results is not None:
            for name_str, names in search_results.items():
                if name_str == '.':
                    for name in names:
                        name.set_actual_value(self.build_address.collapse())
                else:
                    equate = self.get_equate(name_str)
                    if equate is None and replace_undefined is not None:
                        class VOID: pass
                        eq = VOID()
                        eq.expression = replace_undefined
                        equate = { 'equate': eq }
                    if equate is not None:
                        for name in names:
                            if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
                                print("=== Line {}: replacing {} with {}".format(line.line_number, name_str, equate['equate'].expression.collapse()))
                            name.set_actual_value(equate['equate'].expression.collapse())
                            
    def replace_macro_arguments(self, line, operand):
        if len(self._macro_arguments) == 0:
            return
        macro_action, current_arguments = self._macro_arguments[-1]
        macro_action.replace_macro_arguments(line, operand, current_arguments, self)

    def get_macro_arguments(self, line):
        if len(self._macro_arguments) == 0:
            return None, None
        return self._macro_arguments[-1]

    def push_flow_control(self, action):
        self._flow_control.append(action)

    def pop_flow_control(self):
        if len(self._flow_control) == 0:
            return None
        return self._flow_control.pop()

    def push_capturing_actions(self, line, action):
        if len(self._capturing_actions) and isinstance(action, CreateMacroAction):
            raise MacroError("Line {}: cannot declare a macro here".format(line.line_number))
        self._capturing_actions.append(action)

    def pop_capturing_actions(self, line):
        if len(self._capturing_actions) == 0:
            raise MacroError("Line {}: unexpected end block".format(line.line_number))
        return self._capturing_actions.pop()

    def add_macro(self, name_str, line, action):
        self.verify_label_available(name_str, line, None)
        self._macros[name_str] = action

    def get_macro(self, name_str):
        return self._macros.get(name_str, None)

    def push_macro_arguments(self, operands):
        self._macro_arguments.append(operands)

    def pop_macro_arguments(self):
        self._macro_arguments.pop()

    def set_build_address(self, address):
        self.build_address = address.collapse()

    def build_code_actions(self):
        for line in self.program:
            self.process_line(line)

    def append_action(self, action, skip_top=False):
        if not skip_top and len(self._capturing_actions):
            self._capturing_actions[-1].append_action(action)
        elif skip_top and len(self._capturing_actions) > 1:
            self._capturing_actions[-2].append_action(action)
        else:
            self.actions.append(action)

    def process_line(self, line):
        if line.equate is not None:
            self._process_equate(line)
        else:
            # Going to special case .MACRO since it uses the label_declaration
            if len(line.statement_list.value) == 0 or line.statement_list.value[0].name.value.upper() != '.MACRO':
                if line.label_declaration is not None:
                    label = LabelDeclarationAction(line, line.label_declaration)
                    self.append_action(label)
                    if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
                        print("*** Created LabelDeclaration: {}".format(line.label_declaration.value))

            for i, statement in enumerate(line.statement_list.value):
                self._process_statement(line, i, statement)
    
    def _process_equate(self, line):
        # Equates must be valid through the processing stage (an equate cannot reference a future equate).
        # They can reference previous equates only
        equate_str = line.equate.name.value
        if equate_str[0] == '@':
            raise InvalidNameError("Line {}: cannot use '@' for equates".format(line.line_number))

        if equate_str in self._all_labels:
            raise InvalidNameError("Line {}: equate redefines label".format(line.line_number))

        self.verify_label_available(line.equate.name.value, line, self.current_segment)

        search_results = line.equate.expression.find_referenced_names()
        #print("equate search results:", search_results)
        if search_results is not None:
            for name_str, referenced_names in search_results.items():
                if name_str in self._equates:
                    for names in referenced_names:
                        names.set_actual_value(self._equates[name_str]['equate'].expression.collapse())

        try:
            line.equate.expression.eval()
            line.equate.final = True
            #print("*** Equate {} is final".format(line.equate.name.value))
        except:
            # Some other thing or token caused a problem processing this expression
            # TODO: actually should we support something like a QuotedString or ExpressionList?
            raise EquateDefinitionError("Line {}: error processing equate '{}'".format(line.line_number, line.equate.name.value))

        self._equates[equate_str] = {
            'line': line,
            'equate': line.equate,
        }

        return True

    def _process_statement(self, line, i, statement):
        name = statement.name.value
        
        if name.upper() != '.MACRO' and statement.has_elipses:
            raise ElipsesNotValidError("Line {}: use of elipses (...) in expression is not valid here".format(line.line_number))

        if name.startswith('.'):
            self._process_s_compiler_directive(line, i, statement)
        elif name in self._macros:
            self._process_s_macro_expansion(line, i, statement)
        elif name.upper() in Assembler.STRUCTURED_LABELS:
            self._process_s_flow_instruction(line, i, statement)
        else:
            self._process_s_instruction(line, i, statement)

    def _process_s_compiler_directive(self, line, i, statement):
        directive = statement.name.value[1:]
        du = directive.upper()

        if du in self._directives:
            self._directives[du](line, i, statement)
        else:
            self._process_s_segment_change(line, i, directive)

    def _process_scd_a8(self, line, i, statement):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to A8".format(line.line_number))
        self.accumulator_mode = 8
        action = SetAccumulator8(line)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SetAccumulator8")

    def _process_scd_a16(self, line, i, statement):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to A16".format(line.line_number))
        self.accumulator_mode = 16
        action = SetAccumulator16(line)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SetAccumulator16")

    def _process_scd_i8(self, line, i, statement):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to I8".format(line.line_number))
        self.index_mode = 8
        action = SetIndex8(line)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SetIndex8")

    def _process_scd_i16(self, line, i, statement):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to I16".format(line.line_number))
        self.index_mode = 16
        action = SetIndex16(line)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SetIndex16")

    def _process_scd_db(self, line, i, statement):
        if len(statement.operands.value) == 0:
            raise IncorrectParameterCountError("Line {}: empty DB".format(line.line_number))
        action = InsertBytes(line, statement.operands)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created bytes: {}".format(str(statement.operands)))

    def _process_scd_dw(self, line, i, statement):
        if len(statement.operands.value) == 0:
            raise IncorrectParameterCountError("Line {}: empty DW".format(line.line_number))
        action = InsertWords(line, statement.operands)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created words: {}".format(str(statement.operands)))

    def _process_scd_dl(self, line, i, statement):
        if len(statement.operands.value) == 0:
            raise IncorrectParameterCountError("Line {}: empty DL".format(line.line_number))
        action = InsertLongs(line, statement.operands)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created longs: {}".format(str(statement.operands)))
         
    def _process_scd_fill(self, line, i, statement):
        if len(statement.operands.value) != 2:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments to FILL".format(line.line_number))
        action = FillBytes(line, statement.operands)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created fill {}".format(str(statement.operands)))

    def _process_scd_fillw(self, line, i, statement):
        if len(statement.operands.value) != 2:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments to FILLW".format(line.line_number))
        action = FillWords(line, statement.operands)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created fill {}".format(str(statement.operands)))

    def _process_scd_global(self, line, i, statement):
        if len(statement.operands.value) < 1:
            raise IncorrectParameterCountError("Line {}: invalid number of arguments to GLOBAL".format(line.line_number))
        for j, operand in enumerate(statement.operands.value):
            if not isinstance(operand, ParserAST.Name):
                raise InvalidParameterError("Line {}: argument {} isn't a label".format(line.line_number, j + 1))
            if operand.value in self._global_labels:
                raise GlobalRedefinitionError("Line {}: argument {} redefines label as global again".format(line.line_number, j + 1))
            if operand.value[0] == '@':
                raise InvalidGlobalError("Line {}: label '{}' can't be global".format(line.line_number, operand.value))
            action = SetGlobal(line, operand)
            self.append_action(action)
            if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
                print("*** Created SetGlobal for {}".format(operand.value))

    def _process_scd_globalall(self, line, i, statement):
        if len(statement.operands.value) > 0:
            raise IncorrectParameterCountError("Line {}: invalid number of arguments to GLOBALALL".format(line.line_number))
        action = SetGlobalAll(line)
        self.append_action(action)
        if self.current_segment is not None:
            self.current_segment.global_all = True
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SetGlobalAll")

    def _process_scd_incbin(self, line, i, statement):
        if len(statement.operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments to FILLW".format(line.line_number))
        if not isinstance(statement.operands.value[0], ParserAST.QuotedString):
            raise InvalidParameterError("Line {}: file name required for INCBIN".format(line.line_number))
        action = IncBinAction(line, statement.operands.value[0])
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created INCBIN: {}".format(str(statement.operands.value[0])))

    def _process_scd_include(self, line, i, statement):
        if len(statement.operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments to INCLUDE".format(line.line_number))
        if not isinstance(statement.operands.value[0], ParserAST.QuotedString):
            raise InvalidParameterError("Line {}: file name required for INCLUDE".format(line.line_number))
        action = IncludeAction(self, line, statement.operands.value[0])
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created INCLUDE: {}".format(str(statement.operands.value[0])))

    def _process_scd_macro(self, line, i, statement):
        action = CreateMacroAction(line, statement, self)
        self.append_action(action, skip_top=True)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created MACRO: {}".format(str(line.label_declaration.value)))

    def _process_scd_endmacro(self, line, i, statement):
        if len(statement.operands.value) != 0:
            raise FeatureNotImplementedError("Line {}: extra parameters to ENDMACRO".format(line.line_number))
        action = EndMacroAction(line, statement, self)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created ENDMACRO")

    def _process_scd_org(self, line, i, statement):
        if len(statement.operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: invalid number of arguments to ORG".format(line.line_number))
        action = SetSegmentOrg(line, statement.operands.value[0])
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SetSegmentOrg: {}".format(str(statement.operands.value[0])))

    def _process_scd_segment(self, line, i, statement):
        '''These segments will assist in writing programs that make use of bank switching'''
        if len(statement.operands.value) != 4:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for SEGMENT".format(line.line_number))
        operands = statement.operands.value
        name, start, size, file_offset = operands
        if not isinstance(name, ParserAST.QuotedString):
            raise InvalidParameterError("Line {}: parameter 1 to SEGMENT is invalid".format(line.line_number))
        for i, v in enumerate((start, size, file_offset)):
            self.replace_equates(line, v)
            try:
                v.collapse()
            except:
                raise InvalidParameterError("Line {}: parameter {} to SEGMENT is invalid".format(line.line_number, i + 2))
        create_segment = CreateSegmentAction(line, name, start, size, file_offset)
        self.append_action(create_segment)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created CreateSegment: {} @ {} (size {}, file_offset {})".format(name.value, str(start), str(size), str(file_offset)))

    def _process_scd_if(self, line, i, statement):
        action = CompilerIfAction(line, statement, self)
        self.append_action(action, skip_top=True)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created IF")

    def _process_scd_elif(self, line, i, statement):
        # ELIF and ELSE don't get added to any action list, because
        # the validates get called from within the IF action
        CompilerElseIfAction(line, statement, self)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created ELIF")

    def _process_scd_else(self, line, i, statement):
        # ELIF and ELSE don't get added to any action list, because
        # the validates get called from within the IF action
        CompilerElseAction(line, statement, self)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created ELSE")

    def _process_scd_endif(self, line, i, statement):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to ENDIF".format(line.line_number))
        action = CompilerEndIfAction(line, statement, self)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created ENDIF")

    def _process_scd_valoop(self, line, i, statement):
        action = CompilerVALoopAction(line, statement, self)
        self.append_action(action, skip_top=True)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created VALOOP")

    def _process_scd_endvaloop(self, line, i, statement):
        action = CompilerEndVALoopAction(line, statement, self)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created ENDVALOOP")

    def _process_s_segment_change(self, line, i, segment_name):
        action = SegmentChangeAction(line, segment_name)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created SegmentChange: {}".format(segment_name))

    def _process_s_macro_expansion(self, line, i, statement):
        action = CallMacroAction(line, statement)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("*** Created CallMacro: {}".format(statement.name.value))

    def _process_s_flow_instruction(self, line, i, statement):
        if statement.name.value.upper() == "IF":
            action = IfAction(line, statement.operands)
        elif statement.name.value.upper() == "ELSE":
            action = ElseAction(line, statement.operands)
        elif statement.name.value.upper() == "ENDIF":
            action = EndIfAction(line, statement.operands)
        elif statement.name.value.upper() == "DO":
            action = DoAction(line, statement.operands)
        elif statement.name.value.upper() == "UNTIL":
            action = UntilAction(line, statement.operands)
        elif statement.name.value.upper() == "FOREVER":
            action = ForeverAction(line, statement.operands)
        elif statement.name.value.upper() == "WHILE":
            action = WhileAction(line, statement.operands)
        elif statement.name.value.upper() == "ENDWHILE":
            action = EndWhileAction(line, statement.operands)
        elif statement.name.value.upper() == "SWITCH":
            action = SwitchAction(line, statement.operands)
        elif statement.name.value.upper() == "CASE":
            action = CaseAction(line, statement.operands)
        elif statement.name.value.upper() == "ENDSWITCH":
            action = EndSwitchAction(line, statement.operands)
        else:
            raise FeatureNotImplementedError("Line {}: {}".format(line.line_number, statement.name.value.upper()))

        self.append_action(action)

        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            if len(statement.operands.value) > 0:
                print("*** Created flow control: {} {}".format(statement.name.value.upper(), str(statement.operands)))
            else:
                print("*** Created flow control: {}".format(statement.name.value))

    def _process_s_instruction(self, line, i, statement):
        action = BuildInstructionAction(line, statement)
        self.append_action(action)
        if self.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            if len(statement.operands.value) > 0:
                print("*** Created instruction: {} {}".format(statement.name.value, str(statement.operands)))
            else:
                print("*** Created instruction: {}".format(statement.name.value))

    def validate_actions(self):
        self.current_segment = None
        self.build_address = None
        self.index_mode = 8
        self.accumulator_mode = 8

        for action in self.actions:
            self.validate_one_action(action)

        if len(self._flow_control) != 0:
            last = self.pop_flow_control()
            raise UnexpectedFlowControlError("Line {}: flow control {} not terminated".format(last.line.line_number, last.__class__.NAME))

    def validate_one_action(self, action):
        required_byte_size = action.validate(self)
        if required_byte_size > 0:
            current_segment = self.require_current_segment(action.line)
        
            self.build_address = ParserAST.BinaryOp_Add(self.build_address, ParserAST.Number(required_byte_size, 'dec', ParserAST.Number.required_bytes(required_byte_size))).collapse()
            if self.build_address.eval() > current_segment.end.eval():
                #raise SegmentOverflowError("Line {}: segment \"{}\" reaches beyond segment limits".format(action.line.line_number, current_segment.name.value))
                print(SegmentOverflowError("Line {}: segment \"{}\" reaches beyond segment limits".format(action.line.line_number, current_segment.name.value)))
        
            current_segment.last_build_address = self.build_address

    def finalize_labels(self):
        for segment in self._segments.values():
            self.current_segment = segment
            self.current_segment.finalize_labels(self)

    def generate_code_object(self, listing_fp):
        self.current_segment = None
        self.build_address = None
        self.index_mode = 8
        self.accumulator_mode = 8

        # reset build addresses
        for segment in self._segments.values():
            segment.last_build_address = segment.start.collapse()

        for action in self.actions:
            self.generate_action_bytes(action, listing_fp)

        segments_by_start = list(self._segments.values())
        segments_by_start.sort(key=lambda s: s.start.eval())

        co = {}
        for segment in segments_by_start:
            if listing_fp is not None:
                listing_segments = segment.get_sorted_listing_segments()
                for addr, txt in listing_segments:
                    listing_fp.write(txt)
            code_chunks = segment.get_code_chunks(self)
            co[segment.name.value.lower()] = {
                'code': code_chunks,
                'size': segment.size.eval(),
                'start': segment.start.eval(),
                'file_offset': segment.file_offset.eval()
            }

        return co

    def generate_action_bytes(self, action, listing_fp):
        action_bytes = action.generate_bytes(self, listing_fp)
        if len(action_bytes) > 0:
            current_segment = self.require_current_segment(action.line)
            current_segment.set_bytes(self.build_address, action_bytes)

            self.build_address = ParserAST.BinaryOp_Add(self.build_address, ParserAST.Number(len(action_bytes), 'dec', ParserAST.Number.required_bytes(len(action_bytes)))).collapse()
            if self.build_address.eval() > self.require_current_segment(action.line).end.eval():
                raise SegmentOverflowError("Line {}: segment \"{}\" reaches beyond segment limits".format(action.line.line_number, self.segment.name.value))

            current_segment.last_build_address = self.build_address.collapse()

class Segment():
    def __init__(self, name, start, size, file_offset, line):
        self.name = name
        self.start = start
        self.size = size
        self.end = ParserAST.BinaryOp_Add(start, size).collapse()
        self.file_offset = file_offset
        self.line = line
        self.last_build_address = start.collapse()
        self.listing_buffer = None
        self.listing_buffer_build_address = None
        self.global_all = False
        
        self._label_declarations = {
        }

        self._label_references = {
        }

        self._bytes = {
        }

        self._listing_buffers = []

    def get_label(self, label_str):
        return self._label_declarations.get(label_str, None)

    def declare_label(self, label_str, label_declaration):
        assert label_str not in self._label_declarations
        self._label_declarations[label_str] = label_declaration

    def make_label_references(self, line, expr, action, build_address):
        search_results = expr.find_referenced_names()
        if search_results is not None:
            for name_str, referenced_names in search_results.items():
                referenced_names = [rn for rn in referenced_names if rn.actual_value is None]
                if name_str.upper() not in Assembler.BUILT_IN_LABELS and len(referenced_names) > 0:
                    lrs = self._label_references.get(name_str, [])
                    lrs.append({'name_str': name_str, 'names': referenced_names, 'action': action, 'line': line, 'build_address': build_address.collapse()})
                    self._label_references[name_str] = lrs

    def finalize_labels(self, program_builder):
        # Only label declarations here (equates above)
        for name_str, references in self._label_references.items():
            # Determine temp label directions
            ldir = 0
            if name_str[0] == '@':
                if name_str[-1] == '+':
                    ldir = 1
                    name_str = name_str[:-1]
                if name_str[-1] == '-':
                    ldir = -1
                    name_str = name_str[:-1]
                
            declaration = program_builder.get_label(name_str)
            if declaration is None:
                raise UndefinedLabelError("Line {} file {}: name \"{}\" used but not defined".format(references[0]['action'].line.line_number, references[0]['action'].line.filename, name_str))

            for reference in references:
                for name in reference['names']:
                    addr = reference['build_address'].eval()
                    j = 0

                    while j < (len(declaration['build_addresses']) - 1) and addr > declaration['build_addresses'][j].eval():
                        j = j + 1

                    if addr < declaration['build_addresses'][j].eval() and j > 0:
                        if ldir < 0:
                            v = declaration['build_addresses'][j-1]
                        elif ldir > 0:
                            v = declaration['build_addresses'][j]
                        else:
                            raise Exception("Line {}: ambiguous reference to '{}'".format(reference['line'].line_number, name_str))
                    elif addr == declaration['build_addresses'][j].eval() and j < len(declaration['build_addresses']) - 1:
                        if ldir < 0:
                            v = declaration['build_addresses'][j]
                        elif ldir > 0:
                            v = declaration['build_addresses'][j+1]
                        else:
                            raise Exception("Line {}: ambiguous reference to '{}'".format(reference['line'].line_number, name_str))
                    else:
                        v = declaration['build_addresses'][j]

                    if name.as_long:
                        name.set_actual_value(v.collapse())
                    else:
                        name.set_actual_value(ParserAST.BinaryOp_And(v.collapse(), ParserAST.Number(0xFFFF, 'hex', 2)).collapse())

    def set_bytes(self, addr, inst):
        addr = addr.eval()
        assert addr not in self._bytes
        self._bytes[addr] = inst

    def get_code_chunks(self, program_builder):
        addrs = list(self._bytes.keys())
        addrs.sort()

        code_chunks = []

        offstart = self.start.eval()
        offs = self.start.eval()
        new_b = []
        for addr in addrs:
            if offs < addr:
                if len(new_b):
                    code_chunks.append((offstart, bytes(new_b)))
                offstart = addr
                offs = offstart
                new_b = []
            b = self._bytes[addr]
            new_b = new_b + list(b)
            offs += len(b)
        if len(new_b):
            code_chunks.append((offstart, bytes(new_b)))
        return code_chunks

    def start_new_listing_segment(self, build_address):
        if self.listing_buffer is not None:
            self._listing_buffers.append((self.listing_buffer_build_address.collapse(), self.listing_buffer.getvalue()))
        self.listing_buffer = io.StringIO()
        self.listing_buffer_build_address = build_address.collapse()
        
        def format_with_address_and_bytes(address, byte_values, inst="", comment=None):
            byte_string = " ".join(["{:02X}".format(i) for i in byte_values])
                                                     # spc       bytes      spc  addr colon bank
            spacing = Assembler.LISTING_SOURCE_COLUMN - 1 - len(byte_string) - 1 - 4 - 1 - 2

            output = "{:02X}:{:04X} {}{}{}".format(address >> 16, address & 0xFFFF, byte_string, " " * spacing, inst)
            if comment is not None:
                left_over = max(0, Assembler.LISTING_COMMENT_COLUMN - len(output))
                self.listing_buffer.write("{}{}{}\n".format(output, " " * left_over, comment))
            else:
                self.listing_buffer.write("{}\n".format(output))

        def format_right_comment(comment):
            spacing = Assembler.LISTING_COMMENT_COLUMN
            self.listing_buffer.write("{}{}\n".format(" " * spacing, comment))

        def format_single_line_left(comment):
                   # bank spc addr spc
            spacing = 2 + 1 + 4 + 1
            self.listing_buffer.write("{}{}\n".format(" " * spacing, comment))

        self.listing_buffer.format_with_address_and_bytes = format_with_address_and_bytes
        self.listing_buffer.format_right_comment = format_right_comment
        self.listing_buffer.format_single_line_left = format_single_line_left

    def get_sorted_listing_segments(self):
        if self.listing_buffer is not None:
            self._listing_buffers.append((self.listing_buffer_build_address.collapse(), self.listing_buffer.getvalue()))
            self.listing_buffer = None
            self.listing_buffer_build_address = None
        self._listing_buffers.sort(key=lambda v: v[0].eval())
        return self._listing_buffers

class BuilderAction():
    def validate(self, program_builder):
        return self._validate(program_builder)

    def _validate(self, program_builder):
        raise NotImplementedError("_validate override not implemented in class {}".format(self.__class__))

    def generate_bytes(self, program_builder, listing_fp):
        return self._generate_bytes(program_builder, listing_fp)

    def _generate_bytes(self, program_builder, listing_fp):
        raise NotImplementedError("_generate_bytes override not implemented in class {}".format(self.__class__))

class CreateSegmentAction(BuilderAction):
    def __init__(self, line, name, start, size, file_offset):
        self.line = line
        self.name = name
        self.start = start
        self.size = size
        self.file_offset = file_offset

    def _validate(self, program_builder):
        segment = Segment(self.name, self.start, self.size, self.file_offset, self.line)
        program_builder.add_segment(segment)
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        if listing_fp is not None:
            foff = self.file_offset.eval()
            if foff >= 0:
                listing_fp.write("\t\t;; segment \"{}\" size = 0x{:04X} start = 0x{:04X} file_offset = 0x{:04X}\n".format(self.name.value, self.size.eval(), self.start.eval(), self.file_offset.eval()))
            else:
                listing_fp.write("\t\t;; segment \"{}\" size = 0x{:04X} start = 0x{:04X} file_offset = \"not present\"\n".format(self.name.value, self.size.eval(), self.start.eval()))
        return bytes()

class SegmentChangeAction(BuilderAction):
    def __init__(self, line, segment_name):
        self.line = line
        self.segment_name = segment_name

    def _validate(self, program_builder):
        segment = program_builder.get_segment(self.segment_name)
        if segment is None:
            raise UnknownCompilerDirectiveError("Line {}: unknown segment name or compiler directive '{}'".format(self.line.line_number, self.segment_name.upper()))
        program_builder.set_current_segment(segment)
        program_builder.set_build_address(segment.last_build_address)
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        segment = program_builder.get_segment(self.segment_name)
        program_builder.set_current_segment(segment)
        program_builder.set_build_address(segment.last_build_address)
        if listing_fp is not None:
            segment.start_new_listing_segment(program_builder.build_address.collapse())
            segment.listing_buffer.write("\n        ;; segment \"{}\", org = 0x{:04X}\n        ;;\n".format(segment.name.value, segment.last_build_address.eval()))
            segment.listing_buffer.write("        ;; Accumulator/Memory = {}-bit, Index registers = {}-bit\n        ;;\n".format(program_builder.accumulator_mode, program_builder.index_mode))
        return bytes()

class SetSegmentOrg(BuilderAction):
    def __init__(self, line, operand):
        self.line = line
        self.operand = operand

    def _validate(self, program_builder):
        # valid arguments:
        #   start
        #   start+<number>;TODO
        #   <number>      ;number must be within the segment boundaries
        #   <expression>  ;TODO -- names will need to be constants only
        current_segment = program_builder.require_current_segment(self.line)
        search_results = self.operand.find_referenced_names()
        starts = []
        if search_results is not None:
            for name_str, names in search_results.items():
                if name_str.upper() == 'START':
                    starts = starts + names
                    for name in names:
                        name.set_actual_value(current_segment.start.collapse())
                else:
                    equate = program_builder.get_equate(name_str)
                    if equate is not None:
                        for name in names:
                            name.set_actual_value(equate['equate'].expression.collapse())
                    else:
                        raise NameNotEvaluatableError("Line {}: cannot collapse name: {}".format(self.line.line_number, name_str), None)
        try:
            v = self.operand.collapse()
            # we got a value
            program_builder.set_build_address(v)
        except:
            raise InvalidParameterError("Line {}: cannot evaluate argument to ORG".format(self.line.line_number))

        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        v = self.operand.collapse()
        if program_builder.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
            print("--- {}: Setting build address to 0x{:04X}".format(program_builder.require_current_segment(self.line).name.value, v.eval()))
        program_builder.set_build_address(v)
        if listing_fp is not None:
            program_builder.current_segment.start_new_listing_segment(program_builder.build_address.collapse())
            #listing_fp.write("\t\t;; set org = 0x{:04X}\n\t\t;;\n".format(v.eval()))
            lb = program_builder.current_segment.listing_buffer
            lb.format_single_line_left(";; set org = 0x{:04X}".format(v.eval()))
            lb.format_single_line_left(";;")
        return bytes()

class LabelDeclarationAction(BuilderAction):
    def __init__(self, line, label):
        self.line = line
        self.label = label

    def _validate(self, program_builder):
        current_segment = program_builder.require_current_segment(self.line)
        if not isinstance(self.label, ParserAST.Name):
            # I don't think this one is possible due to the Parser syntax
            raise Exception("Line {}: invalid label".format(self.line.line_number))
        new = program_builder.declare_label_here(self.label.value, self.line)
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== {}: declared label {} @ 0x{:04X}".format(current_segment.name.value, self.label.value, new['build_addresses'][-1].eval()))
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            lb.format_single_line_left(";; {}:".format(self.label.value))
        return bytes()

class BuildInstructionAction(BuilderAction):
    def __init__(self, line, statement):
        assert isinstance(statement, ParserAST.Statement)
        self.line = line
        self.statement = statement

    def _validate(self, program_builder):
        opcodes = program_builder.assembler.opcodes

        # determine if opcode is valid -- get set of possible addressing modes
        addressing_modes = opcodes.get_addressing_modes(self.statement.name.value)
        if addressing_modes is None:
            raise UnknownOpcodeError("Line {}: unknown opcode '{}'".format(self.line.line_number, self.statement.name.value))

        # Replace all the macro arguments
        for operand in self.statement.operands.value:
            program_builder.replace_macro_arguments(self.line, operand)

        # Complete all the name_references that reference equates now
        program_builder.replace_equates(self.line, self.statement.operands)

        # and create all references to labels
        program_builder.make_label_references(self.line, self.statement.operands, self)

        addressing_mode_checks = [
            (Opcodes.OpcodeDatabase.AddressingMode.IMPLIED                          , lambda f: self._validate_implied(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.ACCUMULATOR                      , lambda f: self._validate_implied(program_builder, f, allow_accumulator=True)),
            (Opcodes.OpcodeDatabase.AddressingMode.BRKCOP                           , lambda f: self._validate_brkcop(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.STACK                            , lambda f: self._validate_stack(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE                        , lambda f: self._validate_immediate(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.BLOCK_MOVE                       , lambda f: self._validate_block_move(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.RELATIVE                         , lambda f: self._validate_relative(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.RELATIVE_LONG                    , lambda f: self._validate_relative_long(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.STACK_RELATIVE                   , lambda f: self._validate_stack_relative(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y, lambda f: self._validate_stack_relative_indirect_indexed_y(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT                           , lambda f: self._validate_direct(program_builder, f)),    # DIRECT needs to be tested before ABSOLUT),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  , lambda f: self._validate_direct_indirect(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             , lambda f: self._validate_direct_indirect(program_builder, f, True)),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 , lambda f: self._validate_direct_indexed(program_builder, f, index_value="X")),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_Y                 , lambda f: self._validate_direct_indexed(program_builder, f, index_value="Y")),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        , lambda f: self._validate_direct_indexed_x_indirect(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        , lambda f: self._validate_direct_indirect_indexed_y(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   , lambda f: self._validate_direct_indirect_indexed_y(program_builder, f, True)),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE                         , lambda f: self._validate_absolute(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               , lambda f: self._validate_absolute_indexed(program_builder, f, index_value="X")),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               , lambda f: self._validate_absolute_indexed(program_builder, f, index_value="Y")),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X_INDIRECT      , lambda f: self._validate_absolute_indexed_x_indirect(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               , lambda f: self._validate_absolute_indexed_y(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    , lambda f: self._validate_absolute_long(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          , lambda f: self._validate_absolute_long_indexed_x(program_builder, f)),  # like DIRECT first, I think _LONG_ needs to be checked las),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT                , lambda f: self._validate_absolute_indirect(program_builder, f)),
            (Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT_LONG           , lambda f: self._validate_absolute_indirect(program_builder, f, want_long=True)),
        ]

        # determine which addressing mode is used and ensure 
        # all parameters to be valid for that given mode
        self.addressing_mode = None
        self.instruction_flags = None
        for a, c in addressing_mode_checks:
            if a in addressing_modes:
                flags = program_builder.assembler.opcodes.get_instruction_flags(self.statement.name.value, a)
                if c(flags):
                    self.addressing_mode = a
                    self.instruction_flags = flags
                    break
        else:
            raise UnknownAddressingModeError("Line {}: could not determine addressing mode for '{}'".format(self.line.line_number, self.statement.name.value))

        # determine byte size for said opcode
        instruction_size = opcodes.get_instruction_size(self.statement.name.value, self.addressing_mode)

        # Special case the immediates
        if self.addressing_mode == Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE:
            flags = opcodes.get_instruction_flags(self.statement.name.value, self.addressing_mode)
            if (flags & Opcodes.OpcodeDatabase.IF_EXTRA_ACCUMULATOR_IMMEDIATE) != 0 and program_builder.accumulator_mode == 16:
                instruction_size += 1
            elif (flags & Opcodes.OpcodeDatabase.IF_EXTRA_INDEX_IMMEDIATE) != 0 and program_builder.index_mode == 16:
                instruction_size += 1

        # some instructions need their own address
        self.build_address = program_builder.build_address.collapse()

        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== {}: Created instruction for {} ({}): {} byte(s)".format(program_builder.require_current_segment(self.line).name.value, self.statement.name.value, self.addressing_mode, instruction_size))
        return instruction_size

    def _validate_implied(self, program_builder, flags, allow_accumulator=False):
        if allow_accumulator:
            if len(self.statement.operands.value) == 1:
                if isinstance(self.statement.operands.value[0], ParserAST.Name):
                    if self.statement.operands.value[0].value.upper() == "A":
                        return True
        return len(self.statement.operands.value) == 0

    def _validate_brkcop(self, program_builder, flags):
        return len(self.statement.operands.value) == 0

    def _validate_stack(self, program_builder, flags):
        return len(self.statement.operands.value) == 0

    def _validate_immediate(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if not isinstance(operand, ParserAST.Immediate): # immediates, well, must be immediate.
            return False

        opsize = operand.value.guess_size()
        if (flags & Opcodes.OpcodeDatabase.IF_EXTRA_ACCUMULATOR_IMMEDIATE) != 0 and program_builder.accumulator_mode == 16 and 0 <= opsize <= 2: 
            return True
        elif (flags & Opcodes.OpcodeDatabase.IF_EXTRA_INDEX_IMMEDIATE) != 0 and program_builder.index_mode == 16 and 0 <= opsize <= 2: 
            return True

        # 1 byte operand is always valid
        if opsize == 1:
            return True

        return False

    def _validate_block_move(self, program_builder, flags):
        if len(self.statement.operands.value) != 2:
            return False

        for v in self.statement.operands.value:
            # TODO, generalize this to operand.is_evaluatable(), operand.get_required_size(), operand.find_referenced_names()?
            if not isinstance(v, ParserAST.Immediate): # immediates, well, must be immediate.
                return False

            opsize = v.value.guess_size()
            if opsize > 1:
                return False

        return True

    def _validate_stack_relative(self, program_builder, flags):
        if len(self.statement.operands.value) != 2:
            return False
        stack = self.statement.operands.value[0]
        index = self.statement.operands.value[1]

        if isinstance(stack, ParserAST.ExpressionList):
            return False
        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != "S":
            return False

        opsize = stack.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_stack_relative_indirect_indexed_y(self, program_builder, flags):
        if len(self.statement.operands.value) != 2:
            return False
        operand = self.statement.operands.value[0]
        indexy = self.statement.operands.value[1]

        if not isinstance(operand, ParserAST.ExpressionList) or len(operand.value) != 2 or operand.long:
            return False
        stack = operand.value[0]
        indexs = operand.value[1]
        if not isinstance(indexs, ParserAST.Name):
            return False
        if not isinstance(indexy, ParserAST.Name):
            return False
        if indexs.value.upper() != "S":
            return False
        if indexy.value.upper() != "Y":
            return False

        opsize = stack.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_direct(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if isinstance(operand, ParserAST.Immediate):
            return False
        elif isinstance(operand, ParserAST.ExpressionList):
            return False

        opsize = operand.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_direct_indexed(self, program_builder, flags, index_value):
        if len(self.statement.operands.value) != 2:
            return False
        direct = self.statement.operands.value[0]
        index = self.statement.operands.value[1]

        if isinstance(direct, ParserAST.ExpressionList):
            return False
        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != index_value:
            return False

        opsize = direct.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_direct_indexed_x_indirect(self, flags, program_builder):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if not isinstance(operand, ParserAST.ExpressionList) or len(operand.value) != 2 or operand.long:
            return False

        direct = operand.value[0]
        index = operand.value[1]

        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != "X":
            return False

        opsize = direct.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_direct_indirect_indexed_y(self, program_builder, flags, want_long=False):
        if len(self.statement.operands.value) != 2:
            return False

        operand = self.statement.operands.value[0]
        index = self.statement.operands.value[1]

        if not isinstance(operand, ParserAST.ExpressionList) or len(operand.value) != 1 or operand.long != want_long:
            return False

        direct = operand.value[0]

        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != "Y":
            return False

        opsize = direct.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_relative(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if isinstance(operand, ParserAST.Immediate):
            opsize = operand.value.guess_size()
            if opsize <= 1:
                return True
        else:
            opsize = operand.guess_size()
            if opsize <= 2:
                return True

        return False

    def _validate_relative_long(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if isinstance(operand, ParserAST.Immediate):
            opsize = operand.value.guess_size()
            if opsize <= 2:
                return True
        else:
            opsize = operand.guess_size()
            if opsize <= 2:
                return True

        return False


    def _validate_absolute(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if isinstance(operand, ParserAST.Immediate):
            return False
        if isinstance(operand, ParserAST.ExpressionList):
            return False

        opsize = operand.guess_size()
        if 0 <= opsize <= 2:
            return True

        return False

    def _validate_direct_indirect(self, program_builder, flags, want_long=False):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if not isinstance(operand, ParserAST.ExpressionList):
            return False
        if operand.long != want_long:
            return False
        if len(operand.value) != 1:
            return False
    
        operand = operand.value[0]
        opsize = operand.guess_size()
        if opsize <= 1:
            return True

        return False

    def _validate_absolute_indexed(self, program_builder, flags, index_value):
        if len(self.statement.operands.value) != 2:
            return False
        absolute = self.statement.operands.value[0]
        index = self.statement.operands.value[1]

        if isinstance(absolute, ParserAST.ExpressionList):
            return False
        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != index_value:
            return False

        opsize = absolute.guess_size()
        if 0 <= opsize <= 2:
            return True

        return False

    def _validate_absolute_indexed_x_indirect(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if not isinstance(operand, ParserAST.ExpressionList) or len(operand.value) != 2 or operand.long:
            return False

        absolute = operand.value[0]
        index = operand.value[1]

        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != "X":
            return False

        opsize = absolute.guess_size()
        if 0 <= opsize <= 2:
            return True

        return False

    def _validate_absolute_long(self, program_builder, flags):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if isinstance(operand, ParserAST.Immediate):
            return False
        if isinstance(operand, ParserAST.ExpressionList):
            return False

        opsize = operand.guess_size()
        if 0 <= opsize <= 3:
            return True

        return False

    def _validate_absolute_long_indexed_x(self, program_builder, flags):
        if len(self.statement.operands.value) != 2:
            return False
        absolute = self.statement.operands.value[0]
        index = self.statement.operands.value[1]

        if isinstance(absolute, ParserAST.ExpressionList):
            return False
        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != "X":
            return False

        opsize = absolute.guess_size()
        if 0 <= opsize <= 3:
            return True

        return False

    def _validate_absolute_indexed_y(self, program_builder, flags):
        if len(self.statement.operands.value) != 2:
            return False
        absolute = self.statement.operands.value[0]
        index = self.statement.operands.value[1]

        if isinstance(absolute, ParserAST.ExpressionList):
            return False
        if not isinstance(index, ParserAST.Name):
            return False
        if index.value.upper() != "Y":
            return False

        opsize = absolute.guess_size()
        if 0 <= opsize <= 2:
            return True

        return False

    def _validate_absolute_indirect(self, program_builder, flags, want_long=False):
        if len(self.statement.operands.value) != 1:
            return False
        operand = self.statement.operands.value[0]

        if not isinstance(operand, ParserAST.ExpressionList) or operand.long != want_long:
            return False
        if len(operand.value) != 1:
            return False
    
        operand = operand.value[0]
        opsize = operand.guess_size()
        if 0 <= opsize <= 2:
            return True

        return False

    def _calculate_relative(self, operands, is_long):
        if is_long:
            distance = operands.eval() - (self.build_address.eval() + 3)
            if distance < -32768 or distance > 32767:
                raise RelativeBranchOutOfRangeError("Line {}: relative long branch out of range ({})".format(self.line.line_number, distance))
            hex_distance = distance & 0xFFFF
            return ParserAST.Number(hex_distance, 'hex', 2)
        else:
            distance = operands.eval() - ((self.build_address.eval() & 0xFFFF) + 2)
            if distance < -128 or distance > 127:
                raise RelativeBranchOutOfRangeError("Line {}: relative branch out of range ({})".format(self.line.line_number, distance))
            hex_distance = distance & 0xFF
            return ParserAST.Number(hex_distance, 'hex', 1)

    def _generate_bytes(self, program_builder, listing_fp):
        opcodes = program_builder.assembler.opcodes
        ret = [opcodes.get_instruction_opcode(self.statement.name.value, self.addressing_mode)]

        size_table = {
            Opcodes.OpcodeDatabase.AddressingMode.BRKCOP                           : ("brkcop", 0, lambda operands: ParserAST.Number(0, 'dec', 1)),
            Opcodes.OpcodeDatabase.AddressingMode.IMPLIED                          : ("implied", 0, lambda operands: None),
            Opcodes.OpcodeDatabase.AddressingMode.ACCUMULATOR                      : ("accumulator", 0, lambda operands: None),
            Opcodes.OpcodeDatabase.AddressingMode.STACK                            : ("stack", 0, lambda operands: None),
            Opcodes.OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : ("stack-relative", 1, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: ("stack-relative-indirect-indexed-y", 1, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.RELATIVE                         : ("relative", 1, lambda operands: self._calculate_relative(operands.value[0], False)),
            Opcodes.OpcodeDatabase.AddressingMode.RELATIVE_LONG                    : ("relative", 2, lambda operands: self._calculate_relative(operands.value[0], True)),
            Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE                        : ("immediate", -1, lambda operands: operands.value[0].value.collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.BLOCK_MOVE                       : ("block-move", 1, lambda operands: (operands.value[0].value.collapse(), operands.value[1].value.collapse())),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT                           : ("direct", 1, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : ("direct-indexed-x", 1, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_Y                 : ("direct-indexed-y", 1, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : ("direct-indexed-x-indirect", 1, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : ("direct-indirect-indexed-y", 1, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : ("direct-indirect", 1, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : ("direct-indirect-long", 1, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : ("direct-indirect-long-indexed-y", 1, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE                         : ("absolute", 2, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : ("absolute-indexed-x", 2, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : ("absolute-indexed-y", 2, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X_INDIRECT      : ("absolute-indexed-x-indirect", 2, lambda operands: operands.value[0].value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT                : ("absolute-indirect", 2, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT_LONG           : ("absolute-indirect-long", 2, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : ("absolute-long", 3, lambda operands: operands.value[0].collapse()),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : ("absolute-long-indexed-x", 3, lambda operands: operands.value[0].collapse()),
        }

        if size_table[self.addressing_mode][1] == 0:
            v = size_table[self.addressing_mode][2](self.statement.operands)
            if v is not None:
                ret.append(v.eval() & 0xFF)
        elif size_table[self.addressing_mode][0] == "immediate":
            v = size_table[self.addressing_mode][2](self.statement.operands)

            flags = program_builder.assembler.opcodes.get_instruction_flags(self.statement.name.value, self.addressing_mode)
            if (flags & Opcodes.OpcodeDatabase.IF_EXTRA_ACCUMULATOR_IMMEDIATE) != 0 and program_builder.accumulator_mode == 16:
                if v.stated_byte_size > 2:
                    raise ParameterTooLargeError("Line {}: argument too large for {}-long-accumulator mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
                v = v.eval()
                ret.append(v & 0xFF)
                ret.append((v >> 8) & 0xFF)
            elif (flags & Opcodes.OpcodeDatabase.IF_EXTRA_INDEX_IMMEDIATE) != 0 and program_builder.index_mode == 16:
                if v.stated_byte_size > 2:
                    raise ParameterTooLargeError("Line {}: argument too large for {}-long-index mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
                v = v.eval()
                ret.append(v & 0xFF)
                ret.append((v >> 8) & 0xFF)
            else:
                if v.stated_byte_size != 1:
                    raise ParameterTooLargeError("Line {}: argument too large for {} mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
                ret.append(v.eval() & 0xFF)
        elif size_table[self.addressing_mode][1] == 1:
            v = size_table[self.addressing_mode][2](self.statement.operands)
            if isinstance(v, tuple):
                if v[0].stated_byte_size != 1 or v[1].stated_byte_size != 1:
                    raise ParameterTooLargeError("Line {}: argument too large for {} mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
                ret.append(v[1].eval() & 0xFF)
                ret.append(v[0].eval() & 0xFF)
            else:
                if v.stated_byte_size != 1:
                    raise ParameterTooLargeError("Line {}: argument too large for {} mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
                ret.append(v.eval() & 0xFF)
        elif size_table[self.addressing_mode][1] == 2:
            v = size_table[self.addressing_mode][2](self.statement.operands)
            if v.stated_byte_size > 2:
                raise ParameterTooLargeError("Line {}: argument too large for {} mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
            v = v.eval()
            ret.append(v & 0xFF)
            ret.append((v >> 8) & 0xFF)
        elif size_table[self.addressing_mode][1] == 3:
            v = size_table[self.addressing_mode][2](self.statement.operands)
            if v.stated_byte_size > 3:
                raise ParameterTooLargeError("Line {}: argument too large for {} mode".format(self.line.line_number, size_table[self.addressing_mode][0]))
            v = v.eval()
            ret.append(v & 0xFF)
            ret.append((v >> 8) & 0xFF)
            ret.append((v >> 16) & 0xFF)
        else:
            raise Exception("Hi, nice to meet you.")

        if listing_fp is not None:
            #bs = " ".join(["{:02X}".format(r) for r in ret])
            #spacing = Assembler.LISTING_SOURCE_COLUMN - 1 - len(bs) - 1 - 4 - 1 - 2
            #program_builder.current_segment.listing_buffer.write("{} {}{}{} {}\n".format(self.build_address.as_segment_address(), bs, " " * spacing, self.statement.name.value.upper(), self._format_operands(ret[1:])))
            lb = program_builder.current_segment.listing_buffer
            lb.format_with_address_and_bytes(self.build_address.eval(), ret, "{} {}".format(self.statement.name.value.upper(), self._format_operands(ret[1:])))
 
        return bytes(ret)

    def _format_operands(self, values):
        return {
            Opcodes.OpcodeDatabase.AddressingMode.BRKCOP                           : lambda v: "0x{:02X}".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.IMPLIED                          : lambda v: "",
            Opcodes.OpcodeDatabase.AddressingMode.ACCUMULATOR                      : lambda v: "A",
            Opcodes.OpcodeDatabase.AddressingMode.STACK                            : lambda v: "",
            Opcodes.OpcodeDatabase.AddressingMode.STACK_RELATIVE                   : lambda v: "0x{:02X}, S".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.STACK_RELATIVE_INDIRECT_INDEXED_Y: lambda v: "(0x{:02X}, S), Y".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.RELATIVE                         : lambda v: "0x{:04X}".format(int.from_bytes(v, 'little', signed=True) + (self.build_address.eval() & 0xFFFF) + 2),
            Opcodes.OpcodeDatabase.AddressingMode.RELATIVE_LONG                    : lambda v: "0x{:04X}".format(int.from_bytes(v, 'little', signed=True) + (self.build_address.eval() & 0xFFFF) + 2),
            Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE                        : lambda v: "#0x{:02X}".format(v[0]) if len(v) == 1 else "#0x{:02X}{:02X}".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.BLOCK_MOVE                       : lambda v: "0x{:02X}, 0x{:02X}".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT                           : lambda v: "0x{:02X}".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X                 : lambda v: "0x{:02X}, X".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_Y                 : lambda v: "0x{:02X}, Y".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDEXED_X_INDIRECT        : lambda v: "(0x{:02X}, X)".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_INDEXED_Y        : lambda v: "(0x{:02X}), Y".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT                  : lambda v: "(0x{:02X})".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG             : lambda v: "[0x{:02X}]".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.DIRECT_INDIRECT_LONG_INDEXED_Y   : lambda v: "[0x{:02X}], Y".format(v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE                         : lambda v: "0x{:02X}{:02X}".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X               : lambda v: "0x{:02X}{:02X}, X".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_Y               : lambda v: "0x{:02X}{:02X}, Y".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDEXED_X_INDIRECT      : lambda v: "(0x{:02X}{:02X}, X)".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT                : lambda v: "(0x{:02X}{:02X})".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_INDIRECT_LONG           : lambda v: "[0x{:02X}{:02X}]".format(v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_LONG                    : lambda v: "0x{:02X}:{:02X}{:02X}".format(v[2], v[1], v[0]),
            Opcodes.OpcodeDatabase.AddressingMode.ABSOLUTE_LONG_INDEXED_X          : lambda v: "0x{:02X}:{:02X}{:02X}, X".format(v[2], v[1], v[0]),
        }[self.addressing_mode](values)

class InsertBytes(BuilderAction):
    def __init__(self, line, operands):
        self.line = line
        self.operands = operands

    def _validate(self, program_builder):
        required_byte_size = 0
        for operand in self.operands.value:
            if isinstance(operand, ParserAST.QuotedString):
                required_byte_size += len(operand.value)
            else:
                program_builder.replace_equates(self.line, operand)
                program_builder.make_label_references(self.line, operand, self)
                required_byte_size += 1
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== {}: DB takes {} bytes".format(program_builder.require_current_segment(self.line).name.value, required_byte_size))
        return required_byte_size

    def _generate_bytes(self, program_builder, listing_fp):
        ret = []

        ba = program_builder.build_address.eval()
        for operand in self.operands.value:
            if isinstance(operand, ParserAST.QuotedString):
                sbytes = list(operand.value.encode("ascii"))
                if operand.petscii:
                    from .tools import AsciiToPetscii
                    sbytes = AsciiToPetscii(sbytes)
                ret = ret + sbytes #TODO support Unicode

                if listing_fp is not None:
                    s = operand.value.encode("ascii")
                    lb = program_builder.current_segment.listing_buffer
                    for x in range(0, len(s), 4):
                        b = s[x:x+4]
                        if x == 0:
                            lb.format_with_address_and_bytes(ba, b, ".DB \"{}\"".format(operand.value))
                        else:
                            lb.format_with_address_and_bytes(ba, b)
                        ba += len(b)
            else:
                v = operand.collapse()
                if v.stated_byte_size > 1:
                    raise ParameterTooLargeError("Line {}: argument to DB is too large".format(self.line.line_number))
                v = v.eval() & 0xFF
                ret.append(v)

                if listing_fp is not None:
                    lb = program_builder.current_segment.listing_buffer
                    lb.format_with_address_and_bytes(ba, [v], ".DB 0x{:02X}".format(v & 0xFF))
                    ba += 1

        return bytes(ret)


class InsertWords(BuilderAction):
    def __init__(self, line, operands):
        self.line = line
        self.operands = operands

    def _validate(self, program_builder):
        required_byte_size = 0

        # Announce label references
        for operand in self.operands.value:
            program_builder.replace_equates(self.line, operand)
            program_builder.make_label_references(self.line, operand, self)
            required_byte_size += 2

        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== {}: DW takes {} bytes".format(program_builder.require_current_segment(self.line).name.value, required_byte_size))
        return required_byte_size

    def _generate_bytes(self, program_builder, listing_fp):
        ret = []

        ba = program_builder.build_address.eval()
        for operand in self.operands.value:
            v = operand.collapse()
            if v.stated_byte_size > 2:
                raise ParameterTooLargeError("Line {}: argument to DW is too large".format(self.line.line_number))
            v = v.eval()
            ret.append(v & 0x00FF)
            ret.append((v >> 8) & 0x00FF)

            if listing_fp is not None:
                lb = program_builder.current_segment.listing_buffer
                lb.format_with_address_and_bytes(ba, [v & 0xFF, (v >> 8) & 0xFF], ".DW 0x{:04X}".format(v & 0xFFFF))
                ba += 2
                
        return bytes(ret)

class InsertLongs(BuilderAction):
    def __init__(self, line, operands):
        self.line = line
        self.operands = operands

    def _validate(self, program_builder):
        required_byte_size = 0

        # Announce label references
        for operand in self.operands.value:
            program_builder.replace_equates(self.line, operand)
            program_builder.make_label_references(self.line, operand, self)
            required_byte_size += 3

        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== {}: DL takes {} bytes".format(program_builder.require_current_segment(self.line).name.value, required_byte_size))
        return required_byte_size

    def _generate_bytes(self, program_builder, listing_fp):
        ret = []

        ba = program_builder.build_address.eval()
        for operand in self.operands.value:
            v = operand.collapse()
            if v.stated_byte_size > 3:
                raise ParameterTooLargeError("Line {}: argument to DL is too large".format(self.line.line_number))
            v = v.eval()
            ret.append(v & 0xFF)
            ret.append((v >> 8) & 0xFF)
            ret.append((v >> 16) & 0xFF)

            if listing_fp is not None:
                lb = program_builder.current_segment.listing_buffer
                lb.format_with_address_and_bytes(ba, [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF], ".DL 0x{:06X}".format(v & 0xFFFFFF))
                ba += 3
                
        return bytes(ret)


class FillBytes(BuilderAction):
    def __init__(self, line, operands):
        self.line = line
        self.operands = operands

    def _validate(self, program_builder):
        required_byte_size = 0

        # Announce label references
        for operand in self.operands.value:
            program_builder.replace_equates(self.line, operand)
            program_builder.make_label_references(self.line, operand, self)

        count = self.operands.value[0]

        try:
            count = count.collapse()
            if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
                print("=== {}: FILL takes {} bytes".format(program_builder.require_current_segment(self.line).name.value, count.eval()))
            return count.eval()
        except:
            raise InvalidParameterError("Line {}: error parsing FILL arguments".format(self.line.line_number))

    def _generate_bytes(self, program_builder, listing_fp):
        ret = []

        count = self.operands.value[0]
        fill_byte = self.operands.value[1]

        try:
            fill_byte = fill_byte.collapse()
            if fill_byte.stated_byte_size != 1:
                raise ParameterTooLargeError("Line {}: fill byte size exceeds 1 byte".format(self.line.line_number))
        except:
            raise InvalidParameterError("Line {}: error parsing FILL arguments".format(self.line.line_number))

        if listing_fp is not None:
            ba = program_builder.build_address.eval()
            lb = program_builder.current_segment.listing_buffer
            for x in range(0, count.eval(), 4):
                c = min(4, count.eval() - x)
                b = [fill_byte.eval()] * c
                if x == 0:
                    lb.format_with_address_and_bytes(ba, b, ".FILL 0x{:04X}, 0x{:02X}".format(count.eval(), fill_byte.eval()))
                else:
                    lb.format_with_address_and_bytes(ba, b)
                ba += len(b)

        return bytes([fill_byte.eval()] * count.eval())

class FillWords(BuilderAction):
    def __init__(self, line, operands):
        self.line = line
        self.operands = operands

    def _validate(self, program_builder):
        required_byte_size = 0

        # Announce label references
        for operand in self.operands.value:
            program_builder.replace_equates(self.line, operand)
            program_builder.make_label_references(self.line, operand, self)
        count = self.operands.value[0]

        try:
            count = count.collapse()
            if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
                print("=== {}: FILLW takes {} bytes".format(program_builder.require_current_segment(self.line).name.value, count.eval() * 2))
            return count.eval() * 2
        except:
            raise InvalidParameterError("Line {}: error parsing FILLW arguments".format(self.line.line_number))

    def _generate_bytes(self, program_builder, listing_fp):
        ret = []

        count = self.operands.value[0]
        fill_word = self.operands.value[1]

        try:
            fill_word = fill_word.collapse()
            if fill_word.stated_byte_size > 2:
                raise ParameterTooLargeError("Line {}: fill byte size exceeds 2 bytes".format(self.line.line_number))
        except:
            raise InvalidParameterError("Line {}: error parsing FILLW arguments".format(self.line.line_number))
        v = fill_word.eval()

        if listing_fp is not None:
            ba = program_builder.build_address.eval()
            lb = program_builder.current_segment.listing_buffer
            for x in range(0, count.eval(), 3):
                b = [fill_word.eval()] * 3
                if x == 0:
                    lb.format_with_address_and_bytes(ba, b, ".FILLW 0x{:04X}, 0x{:04X}".format(count.eval(), fill_word.eval()))
                else:
                    lb.format_with_address_and_bytes(ba, b)
                ba += len(b)

        return bytes([(v & 0xFF), ((v >> 8) & 0x0FF)] * count.eval())

class SetAccumulator8(BuilderAction):
    def __init__(self, line):
        self.line = line

    def _validate(self, program_builder):
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== Setting accumulator to 8 bits")
        program_builder.accumulator_mode = 8
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        program_builder.accumulator_mode = 8
        return bytes()

class SetAccumulator16(BuilderAction):
    def __init__(self, line):
        self.line = line

    def _validate(self, program_builder):
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== Setting accumulator to 16 bits")
        program_builder.accumulator_mode = 16
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        program_builder.accumulator_mode = 16
        return bytes()

class SetIndex8(BuilderAction):
    def __init__(self, line):
        self.line = line

    def _validate(self, program_builder):
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== Setting index to 8 bits")
        program_builder.index_mode = 8
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        program_builder.index_mode = 8
        return bytes()

class SetIndex16(BuilderAction):
    def __init__(self, line):
        self.line = line

    def _validate(self, program_builder):
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== Setting index to 16 bits")
        program_builder.index_mode = 16
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        program_builder.index_mode = 16
        return bytes()

class SetGlobal(BuilderAction):
    def __init__(self, line, label):
        self.line = line
        self.label = label

    def _validate(self, program_builder):
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== Setting label {} to global from segment {}".format(label.value, cs.name.value))
        program_builder.set_global_label(self.line, self.label.value)
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        program_builder.accumulator_mode = 8
        return bytes()

class SetGlobalAll(BuilderAction):
    def __init__(self, line):
        self.line = line

    def _validate(self, program_builder):
        cs = program_builder.require_current_segment(self.line)
        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== Setting GLOBAL_ALL on segment {}".format(cs.name.value))
        cs.global_all = True
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        program_builder.accumulator_mode = 8
        return bytes()


class IncBinAction(BuilderAction):
    def __init__(self, line, filename):
        self.line = line
        self.filename = filename

    def _validate(self, program_builder):
        with open(self.filename.value, "rb") as fp:
            self.data = fp.read()

        if program_builder.assembler.verbose >= Assembler.VERBOSE_BUILD:
            print("=== {}: INCBIN \"{}\" is {} bytes".format(program_builder.require_current_segment(self.line).name.value,
                                                             self.filename.value, len(self.data)))
        return len(self.data)

    def _generate_bytes(self, program_builder, listing_fp):
        if listing_fp is not None:
            ba = program_builder.build_address.eval()
            lb = program_builder.current_segment.listing_buffer
            for x in range(0, len(self.data), 4):
                b = self.data[x:x+4]
                if x == 0:
                    lb.format_with_address_and_bytes(ba, b, ".INCBIN \"{}\"".format(self.filename))
                else:
                    lb.format_with_address_and_bytes(ba, b)
                ba += len(b)
        return self.data

class IncludeAction(BuilderAction):
    def __init__(self, program_builder, line, filename):
        self.program_builder = program_builder
        self.line = line
        self.filename = filename

        try:
            with open(filename.value, "r") as fp:
                content = fp.read()
        except OSError:
            for path in program_builder.assembler.include_path:
                if not os.path.isabs(filename.value):
                    newfname = os.path.sep.join([path, filename.value])
                    try:
                        with open(newfname, "r") as fp:
                            content = fp.read()
                            break
                    except OSError:
                        continue
            else:
                raise FileNotFoundError("Could not locate file '{}'".format(filename.value))

        if program_builder.assembler.verbose >= program_builder.assembler.VERBOSE_BASIC:
            print("including {}".format(filename.value))
        self.program = program_builder.assembler.parse_string(content, fn=filename.value, included_from=line)
        for line in self.program:
            program_builder.process_line(line)

    def _validate(self, program_builder):
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        return bytes()

class IfAction(BuilderAction):
    NAME = "IF"

    def __init__(self, line, operands):
        if len(operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for IF".format(line.line_number))
        if operands.value[0].value.upper() not in ("Z_SET", "Z_CLEAR", "C_SET", "C_CLEAR", "N_SET", "N_CLEAR", "V_SET", "V_CLEAR"):
            raise InvalidParameterError("Line {}: parameter 1 must be one of Z_SET, Z_CLEAR, C_SET, C_CLEAR, N_SET, N_CLEAR, V_SET or V_CLEAR".format(line.line_number))

        self.line = line
        self.condition = operands.value[0].value.upper()
        self.else_location = None
        self.endif_action = None

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        program_builder.push_flow_control(self)
        return 2 # Flow control is always a relative branch TODO: relative branches that are too far could use long branches, but we won't know how long the branch is until we parse the code..

    def set_else(self, program_builder):
        self.else_location = program_builder.build_address.collapse()

    def set_endif(self, program_builder):
        self.endif_location = program_builder.build_address.collapse()

    def _generate_bytes(self, program_builder, listing_fp):
        # Swap the conditions because IF branches if the condition is not set
        inst = {
            'C_CLEAR': "BCS",
            'N_CLEAR': "BMI",
            'V_CLEAR': "BVS",
            'Z_CLEAR': "BEQ",
            'C_SET':   "BCC",
            'N_SET':   "BPL",
            'V_SET':   "BVC",
            'Z_SET':   "BNE",
        }[self.condition]
        opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)

        if self.else_location is not None:
            # extra two bytes for the BRA that ends this IF segment
            distance = (self.else_location.eval() + 2) - (program_builder.build_address.eval() + 2)
            if distance < -128 or distance > 127:
                raise RelativeBranchOutOfRangeError("Line {}: IF/ELSE section too large".format(self.line.line_number))
            hex_distance = distance & 0xFF
            ret = bytes([opcode, hex_distance])
        else:
            distance = self.endif_location.eval() - (program_builder.build_address.eval() + 2)
            if distance < -128 or distance > 127:
                raise RelativeBranchOutOfRangeError("Line {}: IF/ENDIF section too large".format(self.line.line_number))
            hex_distance = distance & 0xFF
            ret = bytes([opcode, hex_distance])

        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            dist_str = "{} 0x{:04X}".format(inst, int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (program_builder.build_address.eval() & 0xFFFF) + 2)
            lb.format_with_address_and_bytes(program_builder.build_address.eval(), ret, dist_str, comment=";; IF {}".format(self.condition))

        return ret

class ElseAction(BuilderAction):
    NAME = "IF-ELSE"

    def __init__(self, line, operands):
        if len(operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to ENDIF".format(line.line_number))

        self.line = line

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        ifaction = program_builder.pop_flow_control()
        if ifaction is None:
            raise UnexpectedFlowControlError("Line {}: unexpected ELSE".format(line.line_number))
        if not isinstance(ifaction, IfAction):
            raise UnmatchedEndIfError("Line {}: ELSE with no matching IF statement".format(line.line_number))
        ifaction.set_else(program_builder)
        self.condition = ifaction.condition
        program_builder.push_flow_control(self)
        return 2

    def set_endif(self, program_builder):
        self.endif_location = program_builder.build_address.collapse()

    def _generate_bytes(self, program_builder, listing_fp):
        opcode = program_builder.assembler.opcodes.get_instruction_opcode("BRA", Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)
        distance = self.endif_location.eval() - (program_builder.build_address.eval() + 2)
        if distance < -128 or distance > 127:
            raise RelativeBranchOutOfRangeError("Line {}: ELSE-ENDIF section too large".format(self.line.line_number))
        hex_distance = distance & 0xFF
        ret = bytes([opcode, hex_distance])

        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            dist_str = "BRA 0x{:04X}".format(int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (program_builder.build_address.eval() & 0xFFFF) + 2)
            lb.format_with_address_and_bytes(program_builder.build_address.eval(), ret, dist_str, comment=";; ELSE !{}".format(self.condition))

        return ret

class EndIfAction(BuilderAction):
    def __init__(self, line, operands):
        if len(operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to ENDIF".format(line.line_number))

        self.line = line

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        ifelseaction = program_builder.pop_flow_control()
        if ifelseaction is None:
            raise UnexpectedFlowControlError("Line {}: unexpected ENDIF".format(self.line.line_number))
        if not isinstance(ifelseaction, IfAction) and not isinstance(ifelseaction, ElseAction):
            raise UnmatchedEndIfError("Line {}: ENDIF with no matching IF statement".format(self.line.line_number))
        ifelseaction.set_endif(program_builder)
        self.condition = ifelseaction.condition
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            lb.format_right_comment(";; ENDIF {}".format(self.condition))
        return bytes()

class DoAction(BuilderAction):
    NAME = "DO"

    def __init__(self, line, operands):
        if len(operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to DO".format(line.line_number))

        self.line = line

    def _validate(self, program_builder):
        self.do_location = program_builder.build_address.collapse()
        program_builder.require_current_segment(self.line)
        program_builder.push_flow_control(self)
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            lb.format_right_comment(";; DO")
        return bytes()

class UntilAction(BuilderAction):
    def __init__(self, line, operands):
        if len(operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for UNTIL".format(line.line_number))
        if operands.value[0].value.upper() not in ("Z_SET", "Z_CLEAR", "C_SET", "C_CLEAR", "N_SET", "N_CLEAR", "V_SET", "V_CLEAR"):
            raise InvalidParameterError("Line {}: parameter 1 must be one of Z_SET, Z_CLEAR, C_SET, C_CLEAR, N_SET, N_CLEAR, V_SET or V_CLEAR".format(line.line_number))

        self.line = line
        self.condition = operands.value[0].value.upper()

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        self.do_action = program_builder.pop_flow_control()
        if self.do_action is None:
            raise UnexpectedFlowControlError("Line {}: unexpected UNTIL".format(line.line_number))
        if not isinstance(self.do_action, DoAction):
            raise UnmatchedEndIfError("Line {}: UNTIL with no matching DO statement".format(line.line_number))
        return 2 # Flow control is always a relative branch TODO: relative branches that are too far could use long branches, but we won't know how long the branch is until we parse the code..

    def _generate_bytes(self, program_builder, listing_fp):
        # Because this 'UNTIL' is until the condition IS met, we invert all these conditions
        inst = {
            'C_CLEAR': "BCS",
            'N_CLEAR': "BMI",
            'V_CLEAR': "BVS",
            'Z_CLEAR': "BEQ",
            'C_SET':   "BCC",
            'N_SET':   "BPL",
            'V_SET':   "BVC",
            'Z_SET':   "BNE",
        }[self.condition]
        opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)

        distance = self.do_action.do_location.eval() - (program_builder.build_address.eval() + 2)
        if distance < -128 or distance > 127:
            raise RelativeBranchOutOfRangeError("Line {}: DO/UNTIL section too large".format(self.line.line_number))
        hex_distance = distance & 0xFF
        ret = bytes([opcode, hex_distance])

        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            dist_str = "{} 0x{:04X}".format(inst, int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (program_builder.build_address.eval() & 0xFFFF) + 2)
            lb.format_with_address_and_bytes(program_builder.build_address.eval(), ret, dist_str, comment=";; UNTIL {}".format(self.condition))
        return ret

class ForeverAction(BuilderAction):
    def __init__(self, line, operands):
        if len(operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters for FOREVER".format(line.line_number))

        self.line = line

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        self.do_action = program_builder.pop_flow_control()
        if self.do_action is None:
            raise UnexpectedFlowControlError("Line {}: unexpected FOREVER".format(line.line_number))
        if not isinstance(self.do_action, DoAction):
            raise UnmatchedEndIfError("Line {}: FOREVER with no matching DO statement".format(line.line_number))

        distance = self.do_action.do_location.eval() - (program_builder.build_address.eval() + 2)
        if distance < -32768 or distance > 32767:
            raise RelativeBranchOutOfRangeError("Line {}: DO/FOREVER section too large".format(self.line.line_number))
        if distance < -127 or distance > 127:
            return 3
        return 2 

    def _generate_bytes(self, program_builder, listing_fp):
        # Because this 'UNTIL' is until the condition IS met, we invert all these conditions

        distance = self.do_action.do_location.eval() - (program_builder.build_address.eval() + 2)
        if distance < -128 or distance > 127:
            # recompute distance because the instruction will be 3 bytes, not 2.
            distance = self.do_action.do_location.eval() - (program_builder.build_address.eval() + 3)
            inst = "BRL"
            opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE_LONG)
            hex_distance = distance & 0xFFFF
            ret = bytes([opcode, hex_distance & 0xFF, (hex_distance >> 8) & 0xFF])
        else:
            inst = "BRA"
            opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)
            hex_distance = distance & 0xFF
            ret = bytes([opcode, hex_distance])

        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            if inst == "BRL":
                dist_str = "{} 0x{:04X}".format(inst, int.from_bytes(hex_distance.to_bytes(2, 'little', signed=False), 'little', signed=True) + (program_builder.build_address.eval() & 0xFFFF) + 3)
            else:
                dist_str = "{} 0x{:02X}".format(inst, int.from_bytes(hex_distance.to_bytes(1, 'little', signed=False), 'little', signed=True) + (program_builder.build_address.eval() & 0xFF) + 2)
            lb.format_with_address_and_bytes(program_builder.build_address.eval(), ret, dist_str, comment=";; FOREVER")
        return ret


class WhileAction(BuilderAction):
    NAME = "WHILE"

    def __init__(self, line, operands):
        if len(operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for WHILE".format(line.line_number))
        if operands.value[0].value.upper() not in ("Z_SET", "Z_CLEAR", "C_SET", "C_CLEAR", "N_SET", "N_CLEAR", "V_SET", "V_CLEAR"):
            raise InvalidParameterError("Line {}: parameter 1 must be one of Z_SET, Z_CLEAR, C_SET, C_CLEAR, N_SET, N_CLEAR, V_SET or V_CLEAR".format(line.line_number))

        self.line = line
        self.condition = operands.value[0].value.upper()

    def _validate(self, program_builder):
        self.while_address = program_builder.build_address.collapse()
        program_builder.require_current_segment(self.line)
        program_builder.push_flow_control(self)
        return 2 # at the beginning of the loop we check the flag

    def set_end_while(self, program_builder):
        self.endwhile_address = program_builder.build_address.collapse()

    def _generate_bytes(self, program_builder, listing_fp):
        # Because this 'UNTIL' is until the condition IS met, we invert all these conditions
        inst = {
            'C_CLEAR': "BCS",
            'N_CLEAR': "BMI",
            'V_CLEAR': "BVS",
            'Z_CLEAR': "BEQ",
            'C_SET':   "BCC",
            'N_SET':   "BPL",
            'V_SET':   "BVC",
            'Z_SET':   "BNE",
        }[self.condition]
        opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)

        distance = (self.endwhile_address.eval() + 2) - (program_builder.build_address.eval() + 2)
        if distance < -128 or distance > 127:
            raise RelativeBranchOutOfRangeError("Line {}: DO/UNTIL section too large".format(self.line.line_number))
        hex_distance = distance & 0xFF
        ret = bytes([opcode, hex_distance])

        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            dist_str = "{} 0x{:04X}".format(inst, int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (program_builder.build_address.eval() & 0xFFFF) + 2)
            lb.format_with_address_and_bytes(program_builder.build_address.eval(), ret, dist_str, ";; WHILE {}".format(self.condition))
 
        return ret

class EndWhileAction(BuilderAction):
    def __init__(self, line, operands):
        if len(operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to ENDWHILE".format(line.line_number))

        self.line = line

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        self.while_action = program_builder.pop_flow_control()
        if self.while_action is None or not isinstance(self.while_action, WhileAction):
            raise UnexpectedFlowControlError("Line {}: unexpected ENDWHILE".format(line.line_number))
        self.while_action.set_end_while(program_builder)
        return 2 # always branch to the beginning of the loop

    def _generate_bytes(self, program_builder, listing_fp):
        inst = {
            'C_CLEAR': "BCC",
            'N_CLEAR': "BPL",
            'V_CLEAR': "BVC",
            'Z_CLEAR': "BNE",
            'C_SET':   "BCS",
            'N_SET':   "BMI",
            'V_SET':   "BVS",
            'Z_SET':   "BEQ",
        }[self.while_action.condition]
        opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)
        distance = (self.while_action.while_address.eval() + 2) - (program_builder.build_address.eval() + 2)
        if distance < -128 or distance > 127:
            raise RelativeBranchOutOfRangeError("Line {}: WHILE/ENDWHILE section too large".format(self.line.line_number))

        opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)
        hex_distance = distance & 0xFF
        ret = bytes([opcode, hex_distance])

        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            dist_str = "{} 0x{:04X}".format(inst, int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (program_builder.build_address.eval() & 0xFFFF) + 2)
            lb.format_with_address_and_bytes(program_builder.build_address.eval(), ret, dist_str, ";; ENDWHILE {}".format(self.while_action.condition))
        return ret

class SwitchAction(BuilderAction):
    NAME = "SWITCH"

    def __init__(self, line, operands):
        if len(operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for SWITCH".format(line.line_number))
        if operands.value[0].value.upper() not in ("A", "X", "Y"):
            raise InvalidParameterError("Line {}: parameter 1 must be one of A, X, or Y".format(line.line_number))

        self.line = line
        self.condition = operands.value[0].value.upper()

    def _validate(self, program_builder):
        program_builder.require_current_segment(self.line)
        program_builder.push_flow_control(self)
        return 0

    def set_end_switch(self, program_builder):
        self.endswitch_address = program_builder.build_address.collapse()

    def _generate_bytes(self, program_builder, listing_fp):
        # SWITCH doesn't generate any code
        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            lb.format_right_comment(";; SWITCH {}".format(self.condition))
        return bytes()

class CaseAction(BuilderAction):
    NAME = "SWITCH"

    def __init__(self, line, operands):
        if len(operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for CASE".format(line.line_number))
        self.immediate = operands.value[0]
        if not isinstance(self.immediate, ParserAST.Immediate):
            raise IncorrectParameterCountError("Line {}: currently only immediate values are supported for CASE".format(line.line_number))
        self.line = line

    def _validate(self, program_builder):
        switch_action = program_builder.pop_flow_control()

        self.prepend_bra = False
        if switch_action is not None and isinstance(switch_action, CaseAction):
            self.prepend_bra = True
            build_address = ParserAST.BinaryOp_Add(program_builder.build_address, ParserAST.Number(2, 'hex', 1)).collapse()
            switch_action.set_next_case(build_address)
            switch_action = switch_action.switch_action

        if switch_action is None or not isinstance(switch_action, SwitchAction):
            raise UnexpectedFlowControlError("Line {}: unexpected CASE".format(line.line_number))

        self.switch_action = switch_action

        try:
            # Complete all the name_references that reference equates now
            program_builder.replace_equates(self.line, self.immediate.value)

            v = self.immediate.value.collapse()
            # Good
            # resulting code will be
            # BRA <endswitch> ... ; sometimes
            # CMP/CPX/CPY #<immediate>
            # BNE <next case> / BNE <endswitch>
            # ... code ...
            # BRA <endswitch> ... ; etc
            program_builder.push_flow_control(self)
            if switch_action.condition == "A":
                if program_builder.accumulator_mode == 16 and v.stated_byte_size <= 2:
                    return 7 if self.prepend_bra else 5
                elif v.stated_byte_size <= 1:
                    return 6 if self.prepend_bra else 4
                else:
                    raise ParameterTooLargeError("Line {}: argument to CASE is too large".format(self.line.line_number))
            else:
                if program_builder.index_mode == 16 and v.stated_byte_size <= 2:
                    return 7 if self.prepend_bra else 5
                elif v.stated_byte_size <= 1:
                    return 6 if self.prepend_bra else 4
                else:
                    raise ParameterTooLargeError("Line {}: argument to CASE is too large".format(self.line.line_number))
        except:
            #raise FeatureNotImplementedError("Line {}: argument to CASE must be evaluatable (no labels)".format(self.line.line_number))
            raise

        raise Exception()

    def set_next_case(self, build_address):
        self.next_case_address = build_address.collapse()

    def _generate_bytes(self, program_builder, listing_fp):
        ret = []
        v = self.immediate.value.collapse()

        build_address = program_builder.build_address.collapse()
        if self.prepend_bra:
            opcode = program_builder.assembler.opcodes.get_instruction_opcode("BRA", Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)
            distance = self.switch_action.endswitch_address.eval() - (program_builder.build_address.eval() + 2)
            if distance < -128 or distance > 127:
                raise RelativeBranchOutOfRangeError("Line {}: CASE/ENDSWITCH distance too large".format(self.line.line_number))
            hex_distance = distance & 0xFF
            addtl = [opcode, hex_distance]
            ret = ret + addtl

            if listing_fp is not None:
                lb = program_builder.current_segment.listing_buffer
                dist_str = "BRA 0x{:04X}".format(int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (build_address.eval() & 0xFFFF) + 2)
                lb.format_with_address_and_bytes(build_address.eval(), ret, dist_str, comment=";; ENDCASE")
            
            build_address = ParserAST.BinaryOp_Add(build_address, ParserAST.Number(len(addtl), 'hex', 1)).collapse()

        if self.switch_action.condition == "A":
            inst = "CMP"
            opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE)
            if program_builder.accumulator_mode == 16:
                v = v.eval()
                addtl = [opcode, v & 0xFF, (v >> 8) & 0xFF]
            else:
                v = v.eval()
                addtl = [opcode, v & 0xFF]
        elif self.switch_action.condition == "X":
            inst = "CPX"
            opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE)
            if program_builder.index_mode == 16:
                v = v.eval()
                addtl = [opcode, v & 0xFF, (v >> 8) & 0xFF]
            else:
                v = v.eval()
                addtl = [opcode, v & 0xFF]
        elif self.switch_action.condition == "Y":
            inst = "CPY"
            opcode = program_builder.assembler.opcodes.get_instruction_opcode(inst, Opcodes.OpcodeDatabase.AddressingMode.IMMEDIATE)
            if program_builder.index_mode == 16:
                v = v.eval()
                addtl = [opcode, v & 0xFF, (v >> 8) & 0xFF]
            else:
                v = v.eval()
                addtl = [opcode, v & 0xFF]

        ret = ret + addtl

        if listing_fp is not None:
            if len(addtl) == 3:
                dist_str = "{} #0x{:04X}".format(inst, v)
                case_str = ";; CASE #0x{:04X}".format(v)
            else:
                dist_str = "{} #0x{:02X}".format(inst, v & 0xFF)
                case_str = ";; CASE #0x{:02X}".format(v & 0xFF)
            lb = program_builder.current_segment.listing_buffer
            lb.format_with_address_and_bytes(build_address.eval(), addtl, dist_str, comment=case_str)
            build_address = ParserAST.BinaryOp_Add(build_address, ParserAST.Number(len(addtl), 'hex', 1)).collapse()

        opcode = program_builder.assembler.opcodes.get_instruction_opcode("BNE", Opcodes.OpcodeDatabase.AddressingMode.RELATIVE)
        distance = self.next_case_address.eval() - (build_address.eval() + 2)
        if distance < -128 or distance > 127:
            raise RelativeBranchOutOfRangeError("Line {}: CASE/ENDSWITCH distance too large".format(self.line.line_number))
        hex_distance = distance & 0xFF
        ret = ret + [opcode, hex_distance]

        if listing_fp is not None:
            dist_str = "{} 0x{:04X}".format("BNE", int.from_bytes(bytes([hex_distance]), 'little', signed=True) + (build_address.eval() & 0xFFFF) + 2)
            lb = program_builder.current_segment.listing_buffer
            lb.format_with_address_and_bytes(build_address.eval(), [opcode, hex_distance], dist_str)

        return ret

class EndSwitchAction(BuilderAction):
    def __init__(self, line, operands):
        if len(operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameters to ENDSWITCH".format(line.line_number))

        self.line = line

    def _validate(self, program_builder):
        switch_action = program_builder.pop_flow_control()
        if switch_action is not None and isinstance(switch_action, CaseAction):
            switch_action.set_next_case(program_builder.build_address)
            switch_action = switch_action.switch_action

        if switch_action is None or not isinstance(switch_action, SwitchAction):
            raise UnexpectedFlowControlError("Line {}: unexpected ENDSWITCH".format(self.line.line_number))

        switch_action.set_end_switch(program_builder)
        self.condition = switch_action.condition
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        # this may generate code if there's a
        if listing_fp is not None:
            lb = program_builder.current_segment.listing_buffer
            lb.format_right_comment(";; ENDSWITCH {}".format(self.condition))
        return bytes()

class CreateMacroAction(BuilderAction):
    def __init__(self, line, statement, program_builder):
        if line.label_declaration is None:
            raise MissingMacroLabelError("Line {}: MACRO requires label definition".format(line.line_number))

        self.line = line
        self.actions = []
        self.operands = statement.operands.value
        self.named_parameters = []
        self.has_varargs = statement.has_elipses

        for operand in self.operands:
            if not isinstance(operand, ParserAST.Name):
                raise InvalidParameterError("Line {}: all arguments to MACRO must be names".format(line.line_number))
            self.named_parameters.append(operand.value)

        program_builder.add_macro(line.label_declaration.value, line, self)
        program_builder.push_capturing_actions(line, self)

    def append_action(self, action):
        self.actions.append(action)

    def call(self):
        return [copy.deepcopy(a) for a in self.actions]

    def set_valoop(self, i, v):
        self.valoop_index = ParserAST.Number(i, 'dec', ParserAST.Number.required_bytes(i))
        self.valoop_value = copy.deepcopy(v)

    def clear_valoop(self):
        self.valoop_index = None
        self.valoop_value = None

    def replace_macro_arguments(self, line, operand, current_arguments, program_builder):
        '''operand - operand that needs names to be replaced
           current_arguments - the list we get the operand value from'''
        search_results = operand.find_referenced_names()
        if search_results is None:
            return

        for name_str, names in search_results.items():
            argument = None

            if name_str[0] == '\\':
                if not self.has_varargs:
                    raise InvalidNameError("Line {}: cannot use vararg values if the macro doesn't accept varargs".format(line.line_number))
                if name_str == "\\L":
                    c = len(current_arguments) - len(self.named_parameters)
                    argument = ParserAST.Number(c, 'dec', ParserAST.Number.required_bytes(c))
                elif name_str == '\\i':
                    if self.valoop_index is None:
                        raise InvalidNameError("Line {}: invalid use of \\i outside of VALOOP".format(line.line_number))
                    argument = self.valoop_index
                elif name_str == '\\v':
                    if self.valoop_index is None:
                        raise InvalidNameError("Line {}: invalid use of \\v outside of VALOOP".format(line.line_number))
                    argument = self.valoop_value
                else:
                    var_index = int(name_str[1:])
                    var_index = var_index + len(self.named_parameters)
                    if var_index < len(current_arguments):
                        argument = current_arguments[var_index]
            else:
                try:
                    arg_index = self.named_parameters.index(name_str)
                    argument = current_arguments[arg_index]
                except ValueError:
                    pass

            if argument is not None:
                for name in names:
                    if program_builder.assembler.verbose >= Assembler.VERBOSE_EVERYTHING:
                        print("=== {}: line {}: replacing {} with {}".format(program_builder.require_current_segment(self.line).name.value, line.line_number, name_str, str(argument)))
                    name.set_actual_value(copy.deepcopy(argument))

    def _validate(self, program_builder):
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        return bytes()

class EndMacroAction(BuilderAction):
    def __init__(self, line, operands, program_builder):
        self.line = line
        ret = program_builder.pop_capturing_actions(line)
        if not isinstance(ret, CreateMacroAction):
            raise MacroError("Line {}: unfinished {}".format(ret.NAME))

    def _validate(self, program_builder):
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        return bytes()

class CallMacroAction(BuilderAction):
    def __init__(self, line, statement):
        self.line = line
        self.statement = statement
        self.operands = statement.operands.value

    def _validate(self, program_builder):
        macro_action = program_builder.get_macro(self.statement.name.value)
        if macro_action is None:
            raise MacroError("Line {}: undefined macro '{}'".format(self.line.line_number, self.statement.name.value))
        self.actions = macro_action.call()
        if (macro_action.has_varargs and len(self.operands) < len(macro_action.named_parameters)) or \
           (not macro_action.has_varargs and len(self.operands) != len(macro_action.named_parameters)):
            raise IncorrectParameterCountError("Line {}: incorrect number of arguments for {}".format(self.line.line_number, self.statement.name.value))
        program_builder.push_macro_arguments((macro_action, self.operands))
        for action in self.actions:
            program_builder.validate_one_action(action)
        program_builder.pop_macro_arguments()
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        for action in self.actions:
            program_builder.generate_action_bytes(action, listing_fp)
        return bytes()

class CompilerIfAction(BuilderAction):
    NAME = "IF"

    def __init__(self, line, statement, program_builder):
        if len(statement.operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: expected only 1 parameter to IF".format(line.line_number))

        self.line = line
        self.expression = statement.operands.value[0]
        self.actions = []
        self.if_block = []
        self.else_action = None

        program_builder.push_capturing_actions(line, self)

    def append_action(self, action):
        self.if_block.append(action)

    def set_else(self, action):
        self.else_action = action

    def _validate(self, program_builder):
        # Replace all the macro arguments
        program_builder.replace_macro_arguments(self.line, self.expression)

        # Complete all the name_references that reference equates now
        program_builder.replace_equates(self.line, self.expression, replace_undefined=ParserAST.Number(0,'dec',1))

        try:
            self.result = self.expression.eval()
            if self.result != 0:
                self.actions = [copy.deepcopy(a) for a in self.if_block]
                for action in self.actions:
                    program_builder.validate_one_action(action)
            elif self.else_action is not None:
                program_builder.validate_one_action(self.else_action)
        except:
            raise
        
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        for action in self.actions:
            program_builder.generate_action_bytes(action, listing_fp)
        if self.else_action is not None:
            return self.else_action.generate_bytes(program_builder, listing_fp)
        return bytes()

class CompilerElseIfAction(BuilderAction):
    NAME = "ELIF"

    def __init__(self, line, statement, program_builder):
        if len(statement.operands.value) != 1:
            raise IncorrectParameterCountError("Line {}: expected only 1 parameter to ELIF".format(line.line_number))

        self.line = line
        self.expression = statement.operands.value[0]
        self.actions = []
        self.elif_block = []
        self.else_action = None

        compiler_if_action = program_builder.pop_capturing_actions(line)
        if not isinstance(compiler_if_action, CompilerIfAction) and not isinstance(compiler_if_action, CompilerElseIfAction):
            raise MacroError("Line {}: unfinished {}".format(line.line_number, compiler_if_action.NAME))
        compiler_if_action.set_else(self)

        program_builder.push_capturing_actions(line, self)

    def append_action(self, action):
        self.elif_block.append(action)

    def set_else(self, action):
        self.else_action = action

    def _validate(self, program_builder):
        # Replace all the macro arguments
        program_builder.replace_macro_arguments(self.line, self.expression)

        # Complete all the name_references that reference equates now
        program_builder.replace_equates(self.line, self.expression, replace_undefined=ParserAST.Number(0,'dec',1))

        try:
            self.result = self.expression.eval()
            if self.result != 0:
                self.actions = [copy.deepcopy(a) for a in self.elif_block]
                for action in self.actions:
                    program_builder.validate_one_action(action)
            elif self.else_action is not None:
                program_builder.validate_one_action(self.else_action)
        except Exception as e:
            raise

        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        for action in self.actions:
            program_builder.generate_action_bytes(action, listing_fp)
        if self.else_action is not None:
            return self.else_action.generate_bytes(program_builder, listing_fp)
        return bytes()

class CompilerElseAction(BuilderAction):
    NAME = "ELSE"

    def __init__(self, line, statement, program_builder):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra arguments to ELSE".format(line.line_number))

        self.line = line
        self.actions = []
        self.else_block = []

        compiler_if_action = program_builder.pop_capturing_actions(line)
        if not isinstance(compiler_if_action, CompilerIfAction) and not isinstance(compiler_if_action, CompilerElseIfAction):
            raise MacroError("Line {}: unfinished {}".format(line.line_number, compiler_if_action.NAME))
        compiler_if_action.set_else(self)

        program_builder.push_capturing_actions(line, self)

    def append_action(self, action):
        self.else_block.append(action)

    def _validate(self, program_builder):
        self.actions = [copy.deepcopy(a) for a in self.else_block]
        for action in self.actions:
            program_builder.validate_one_action(action)

        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        for action in self.actions:
            program_builder.generate_action_bytes(action, listing_fp)
        return bytes()

class CompilerEndIfAction(BuilderAction):
    def __init__(self, line, operands, program_builder):
        self.line = line
        ret = program_builder.pop_capturing_actions(line)
        if not isinstance(ret, CompilerIfAction) and not isinstance(ret, CompilerElseIfAction) and not isinstance(ret, CompilerElseAction):
            raise MacroError("Line {}: unfinished {}".format(line.line_number, ret.NAME))

    def _validate(self, program_builder):
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        return bytes()

class CompilerVALoopAction(BuilderAction):
    NAME = "VALOOP"

    def __init__(self, line, statement, program_builder):
        if len(statement.operands.value) != 0:
            raise IncorrectParameterCountError("Line {}: extra parameter to VALOOP".format(line.line_number))

        self.line = line
        self.actions = []
        self.loop_block = []

        program_builder.push_capturing_actions(line, self)

    def append_action(self, action):
        self.loop_block.append(action)

    def _validate(self, program_builder):
        macro_action, current_arguments = program_builder.get_macro_arguments(self.line)
        if macro_action is None:
            raise VALoopWithoutMacroError("Line {}: VALOOP used outside of macro".format(self.line.line_number))

        lp = len(macro_action.named_parameters)
        tp = len(current_arguments)

        for i in range(tp - lp):
            v = current_arguments[i]
            macro_action.set_valoop(i, v)
            actions = [copy.deepcopy(a) for a in self.loop_block]
            for action in actions:
                program_builder.validate_one_action(action)
            self.actions = self.actions + actions
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        for action in self.actions:
            program_builder.generate_action_bytes(action, listing_fp)
        return bytes()

class CompilerEndVALoopAction(BuilderAction):
    def __init__(self, line, operands, program_builder):
        self.line = line
        ret = program_builder.pop_capturing_actions(line)
        if not isinstance(ret, CompilerVALoopAction):
            raise MacroError("Line {}: unfinished {}".format(line.line_number, ret.NAME))

    def _validate(self, program_builder):
        return 0

    def _generate_bytes(self, program_builder, listing_fp):
        return bytes()

