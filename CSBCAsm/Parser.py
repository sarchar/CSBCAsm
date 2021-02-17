import math

from rply import ParserGenerator, Token

from . import ParserAST

class ParseError(Exception):
    pass

def CreateParser():
    rply_parser = ParserGenerator(
        [
            'DEC_NUMBER', 'HEX_NUMBER', 'OCT_NUMBER', 'BIN_NUMBER',
            'NAME', 'QUOTED_STRING',
            'OPEN_PAREN', 'CLOSE_PAREN', 'OPEN_BRACKET', 'CLOSE_BRACKET',
            'PLUS', 'MINUS', 'MULTIPLY', 'DIVIDE', 'POWER', 'MOD',
            'AND', 'XOR', 'OR', 'BITNOT',
            'LEFT_SHIFT', 'RIGHT_SHIFT',
            'EXPRESSION_SEPARATOR', 'STATEMENT_SEPARATOR', 
            'EQUAL', 'IMMEDIATE',
            'LOW_BYTE', 'HIGH_BYTE',
            'ELIPSES',
            'EQUAL_TO', 'NOT_EQUAL_TO',
            'GREATER_THAN_OR_EQUAL_TO', 'LESS_THAN_OR_EQUAL_TO',
            'LOGICAL_NOT', 'LOGICAL_OR', 'LOGICAL_AND',
        ],
        # same as https://www.programiz.com/python-programming/precedence-associativity and many other programming languages
        precedence=[
            ('left', ['LINE', 'STATEMENT_SEPARATOR']),
            ('left', ['LOGICAL_OR']),
            ('left', ['LOGICAL_AND']),
            ('left', ['LOGICAL_NOT']),
            ('left', ['EQUAL_TO', 'NOT_EQUAL_TO', 'LOW_BYTE', 'HIGH_BYTE', 'GREATER_THAN_OR_EQUAL_TO', 'LESS_THAN_OR_EQUAL_TO']),
            ('left', ['OR']),
            ('left', ['XOR']),
            ('left', ['AND']),
            ('left', ['LEFT_SHIFT', 'RIGHT_SHIFT']),
            ('left', ['PLUS', 'MINUS']),
            ('left', ['MULTIPLY', 'DIVIDE', 'MOD']),
            ('right', ['UPLUS', 'UMINUS', 'UBITNOT', 'LOHI_BYTE', 'ULONG']),
            ('left', ['POWER']),
            ('left', ['EXPRESSION_SEPARATOR']),
            ('left', ['IMMEDIATE']),
            ('left', ['PARENTHESES']),
        ]
    )

    @rply_parser.production('line : statement-list STATEMENT_SEPARATOR')
    @rply_parser.production('line : statement-list')
    @rply_parser.production('line : equate')
    @rply_parser.production('line : ')
    def line(p):
        if len(p) == 0:
            return ParserAST.Line()
        if isinstance(p[0], ParserAST.Equate):
            return ParserAST.Line(equate=p[0])
        sl = p[0]
        stmt_one = sl.value[0]
        label_declaration = None
        if stmt_one.name.column == 1:
            if len(stmt_one.operands.value) > 0:
                raise ParseError("Line {}: unexpected words after '{}'".format(stmt_one.name.line, stmt_one.name.value))
            label_declaration = stmt_one.name
            sl.pop_first()
        if len(p) == 2 and len(sl.value) != 0:
            raise ParseError("Line {}: trailing statement separator".format(p[1].getsourcepos().lineno))
        return ParserAST.Line(statement_list=sl, label_declaration=label_declaration)

    @rply_parser.production('equate : simple-label EQUAL expression')
    def equate(p):
        return ParserAST.Equate(p[0], p[2])

    @rply_parser.production('statement-list : statement-list STATEMENT_SEPARATOR statement', precedence='STATEMENT_SEPARATOR')
    @rply_parser.production('statement-list : statement', precedence='STATEMENT_SEPARATOR')
    def statement_list(p):
        if isinstance(p[0], ParserAST.StatementList) and len(p) == 3:
            sl = p[0]
            sl.append_statement(p[2])
        else:
            sl = ParserAST.StatementList()
            sl.append_statement(p[0])
        return sl

    @rply_parser.production('statement : simple-label expression-list EXPRESSION_SEPARATOR ELIPSES')
    @rply_parser.production('statement : simple-label expression-list')
    @rply_parser.production('statement : simple-label ELIPSES')
    @rply_parser.production('statement : simple-label')
    def statement(p):
        if len(p) == 1:
            st = ParserAST.Statement(p[0], ParserAST.ExpressionList())
        elif len(p) == 2:
            if isinstance(p[1], Token):
                st = ParserAST.Statement(p[0], ParserAST.ExpressionList(), has_elipses=True)
            else:
                st = ParserAST.Statement(p[0], p[1])
        elif len(p) == 4:
            st = ParserAST.Statement(p[0], p[1], has_elipses=True)
        return st

    # According to https://stackoverflow.com/questions/6416752/ply-quickly-parsing-long-lists-of-items
    # It's better to write the list as:
    @rply_parser.production('expression-list : expression-list EXPRESSION_SEPARATOR expression', precedence='EXPRESSION_SEPARATOR')
    @rply_parser.production('expression-list : expression', precedence='EXPRESSION_SEPARATOR')
    def expression_list(p):
        if isinstance(p[0], ParserAST.ExpressionList) and len(p) == 3:
            el = p[0]
            el.append_expression(p[2])
        else:
            el = ParserAST.ExpressionList()
            el.append_expression(p[0])
        return el

    @rply_parser.production('expression : IMMEDIATE expression')
    def immediate_expression(p):
        return ParserAST.Immediate(p[1])

    @rply_parser.production('expression : OPEN_PAREN expression-list CLOSE_PAREN', precedence='PARENTHESES')
    @rply_parser.production('expression : OPEN_BRACKET expression-list CLOSE_BRACKET', precedence='PARENTHESES')
    def expression_parentheses(p):
        # The syntax of assembly requires knowledge of what things are grouped together...For example
        #   LDA (0x1234),Y
        # Even though we can just reduce the first value to remove the parentheses, they're 
        # important in determining addressing modes
        ee = p[1]
        if p[0].gettokentype() == 'OPEN_BRACKET':
            ee.long = True
        return ee

    @rply_parser.production('expression : expression PLUS expression')
    @rply_parser.production('expression : expression MINUS expression')
    @rply_parser.production('expression : expression MULTIPLY expression')
    @rply_parser.production('expression : expression DIVIDE expression')
    @rply_parser.production('expression : expression POWER expression')
    @rply_parser.production('expression : expression AND expression')
    @rply_parser.production('expression : expression XOR expression')
    @rply_parser.production('expression : expression OR expression')
    @rply_parser.production('expression : expression MOD expression')
    @rply_parser.production('expression : expression LEFT_SHIFT expression')
    @rply_parser.production('expression : expression RIGHT_SHIFT expression')
    @rply_parser.production('expression : expression EQUAL_TO expression')
    @rply_parser.production('expression : expression NOT_EQUAL_TO expression')
    @rply_parser.production('expression : expression LOW_BYTE expression')  # unfortunate name, but I can't be bothered to change this atm
    @rply_parser.production('expression : expression HIGH_BYTE expression')
    @rply_parser.production('expression : expression GREATER_THAN_OR_EQUAL_TO expression')
    @rply_parser.production('expression : expression LESS_THAN_OR_EQUAL_TO expression')
    @rply_parser.production('expression : expression LOGICAL_OR expression')
    @rply_parser.production('expression : expression LOGICAL_AND expression')
    def expression(p):
        left = p[0]
        right = p[2]
        op = p[1]
        p = None
        if op.gettokentype() == 'PLUS':
            p = ParserAST.BinaryOp_Add(left, right)
        elif op.gettokentype() == 'MINUS':
            p = ParserAST.BinaryOp_Sub(left, right)
        elif op.gettokentype() == 'MULTIPLY':
            p = ParserAST.BinaryOp_Mul(left, right)
        elif op.gettokentype() == 'DIVIDE':
            p = ParserAST.BinaryOp_Div(left, right)
        elif op.gettokentype() == 'POWER':
            p = ParserAST.BinaryOp_Pow(left, right)
        elif op.gettokentype() == 'MOD':
            p = ParserAST.BinaryOp_Mod(left, right)
        elif op.gettokentype() == 'AND':
            p = ParserAST.BinaryOp_And(left, right)
        elif op.gettokentype() == 'XOR':
            p = ParserAST.BinaryOp_Xor(left, right)
        elif op.gettokentype() == 'OR':
            p = ParserAST.BinaryOp_Or(left, right)
        elif op.gettokentype() == 'LEFT_SHIFT':
            p = ParserAST.BinaryOp_LeftShift(left, right)
        elif op.gettokentype() == 'RIGHT_SHIFT':
            p = ParserAST.BinaryOp_RightShift(left, right)
        elif op.gettokentype() == 'EQUAL_TO':
            p = ParserAST.BinaryOp_EqualTo(left, right)
        elif op.gettokentype() == 'NOT_EQUAL_TO':
            p = ParserAST.BinaryOp_NotEqualTo(left, right)
        elif op.gettokentype() == 'LOW_BYTE':
            p = ParserAST.BinaryOp_LessThan(left, right)
        elif op.gettokentype() == 'HIGH_BYTE':
            p = ParserAST.BinaryOp_GreaterThan(left, right)
        elif op.gettokentype() == 'GREATER_THAN_OR_EQUAL_TO':
            p = ParserAST.BinaryOp_GreaterThanOrEqualTo(left, right)
        elif op.gettokentype() == 'LESS_THAN_OR_EQUAL_TO':
            p = ParserAST.BinaryOp_LessThanOrEqualTo(left, right)
        elif op.gettokentype() == 'LOGICAL_AND':
            p = ParserAST.BinaryOp_LogicalAnd(left, right)
        elif op.gettokentype() == 'LOGICAL_OR':
            p = ParserAST.BinaryOp_LogicalOr(left, right)
        return p

    @rply_parser.production('expression : MINUS expression', precedence='UMINUS')
    def expression_uminus(p):
        neg = ParserAST.UnaryOp_Negate(p[1])
        return neg

    @rply_parser.production('expression : PLUS expression', precedence='UPLUS')
    def expression_uplus(p):
        pos = ParserAST.UnaryOp_Posigate(p[1]) #lul
        return pos

    @rply_parser.production('expression : BITNOT expression', precedence='UBITNOT')
    def expression_uplus(p):
        pos = ParserAST.UnaryOp_Not(p[1])
        return pos

    @rply_parser.production('expression : LOW_BYTE expression', precedence='LOHI_BYTE')
    def expression_ulowbyte(p):
        pos = ParserAST.UnaryOp_LowByte(p[1])
        return pos

    @rply_parser.production('expression : HIGH_BYTE expression', precedence='LOHI_BYTE')
    def expression_uhighbyte(p):
        pos = ParserAST.UnaryOp_HighByte(p[1])
        return pos

    @rply_parser.production('expression : LOGICAL_NOT expression', precedence='LOGICAL_NOT')
    def expression_logicalnot(p):
        pos = ParserAST.UnaryOp_LogicalNot(p[1])
        return pos

    @rply_parser.production('expression : DEC_NUMBER')
    def dec_number(p):
        v = int(p[0].getstr(), 10)
        if v == 0 or v == 1:
            nbytes = 1
        else:
            nbits = math.floor(math.log2(v)) + 1
            nbytes = (nbits + 7) // 8
        n = ParserAST.Number(v, 'dec', nbytes)
        return n

    @rply_parser.production('expression : OCT_NUMBER')
    def oct_number(p):
        v = p[0].getstr()
        if v[0] == '&':
            v = int(v[1:], 8)
        else:
            v = int(v[2:], 8)
        if v == 0 or v == 1:
            nbytes = 1
        else:
            nbits = math.floor(math.log2(v)) + 1
            nbytes = (nbits + 7) // 8
        n = ParserAST.Number(v, 'oct', nbytes)
        return n

    @rply_parser.production('expression : HEX_NUMBER')
    def hex_number(p):
        v = p[0].getstr().replace(":","")
        if v[:2] == '0x' and len(v) > 2:
            n = ParserAST.Number(int(v[2:], 16), 'hex', (len(v[2:]) + 1) // 2) # using the number of typed digits is how you infer direct-page, absolute
        elif v[0] == '$' and len(v) > 1:
            n = ParserAST.Number(int(v[1:], 16), 'hex', (len(v[1:]) + 1) // 2)
        else:
            raise ValueError(p[0])
        return n

    @rply_parser.production('expression : BIN_NUMBER')
    def bin_number(p):
        v = p[0].getstr().replace('_', '')
        if v[0] == '%':
            v = v[1:]
        else:
            v = v[2:]
        nbits = len(v)
        nbytes = (nbits + 7) // 8
        n = ParserAST.Number(int(v, 2), 'bin', nbytes)
        return n

    @rply_parser.production('expression : QUOTED_STRING')
    def quoted_string(p):
        s = p[0].getstr()
        if s[0] == 'p':
            qs = ParserAST.QuotedString(s[2:-1], petscii=True)
        else:
            qs = ParserAST.QuotedString(s[1:-1])
        return qs

    @rply_parser.production('expression : NAME')
    @rply_parser.production('expression : AND NAME')
    def expression_name(p):
        if len(p) == 1:
            name = ParserAST.Name(p[0].getstr(), p[0].getsourcepos().lineno, p[0].getsourcepos().colno, as_long=False)
        else:
            name = ParserAST.Name(p[1].getstr(), p[1].getsourcepos().lineno, p[1].getsourcepos().colno, as_long=True)
        return name

    @rply_parser.production('simple-label : NAME')
    @rply_parser.production('simple-label : PLUS')
    def simple_label(p):
        lbl = ParserAST.Name(p[0].getstr(), p[0].getsourcepos().lineno, p[0].getsourcepos().colno)
        return lbl

    @rply_parser.error
    def error_handler(token):
        if token.getstr() == '$end':
            raise ParseError("unexpected eof")
        else:
            raise ParseError("Line {}: unexpected '{}'".format(token.getsourcepos().lineno, token.getstr()))
        
    return rply_parser.build()
