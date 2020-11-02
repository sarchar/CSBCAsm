from rply import LexerGenerator

def CreateLexer():
    # Tokens should be ordered by decreasing length
    # See http://www.dabeaz.com/ply/ply.html
    rply_lexer = LexerGenerator()

    # Ignore single line comments
    rply_lexer.ignore(r';[^\n]*')
    rply_lexer.ignore(r'//[^\n]*')
    rply_lexer.ignore(r'/\*[^\n]*\*/')

    rply_lexer.add("MULTILINE_COMMENT_START", r'\/\*.*$')
    rply_lexer.add("MULTILINE_COMMENT_END", r'^.*\*\/')

    rply_lexer.add("QUOTED_STRING", r'(p)?\"(\\\"|[^\r\n\"])*\"')

    rply_lexer.add("ELIPSES", r'\.\.\.')
    rply_lexer.add("NAME", r'([a-zA-Z_\.][a-zA-Z_0-9]*)|(\.)|(@[0-9]+(\+|\-)?)|(\\([0-9]+|[Liv]))') #TODO \I and \V

    rply_lexer.add("HEX_NUMBER", r'(\$|0x)[a-fA-F0-9:]+')
    rply_lexer.add("OCT_NUMBER", r'(\&|0o)[0-7]+')
    rply_lexer.add("BIN_NUMBER", r'(%|0b)[0-1_]+')
    rply_lexer.add("DEC_NUMBER", r'[0-9]+')


    #must be before Less than/Greater than
    rply_lexer.add("LEFT_SHIFT", r'<<')
    rply_lexer.add("RIGHT_SHIFT", r'>>')

    rply_lexer.add("EQUAL_TO", "==")
    rply_lexer.add("NOT_EQUAL_TO", "!=")
    rply_lexer.add("NOT_EQUAL_TO", "<>")
    rply_lexer.add("GREATER_THAN_OR_EQUAL_TO", ">=")
    rply_lexer.add("LESS_THAN_OR_EQUAL_TO", "<=")

    rply_lexer.add("LOGICAL_NOT", r"!")
    rply_lexer.add("LOGICAL_OR", r"\|\|")
    rply_lexer.add("LOGICAL_AND", r"\&\&")

    # Shortest tokens at the bottom
    rply_lexer.add("PLUS", r'\+')
    rply_lexer.add("MINUS", r'-')
    rply_lexer.add("POWER", r'\*\*') #must be before MULTIPLY
    rply_lexer.add("MULTIPLY", r'\*')
    rply_lexer.add("DIVIDE", r'/')
    rply_lexer.add("AND", r'&')
    rply_lexer.add("XOR", r'\^')
    rply_lexer.add("OR", r'\|')
    rply_lexer.add("BITNOT", r'~')
    rply_lexer.add("MOD", r'%')
    rply_lexer.add("EQUAL", r'=')
    rply_lexer.add("IMMEDIATE", r'#')

    rply_lexer.add("LOW_BYTE", r'<')
    rply_lexer.add("HIGH_BYTE", r'>')

    rply_lexer.add("OPEN_PAREN", r'\(')
    rply_lexer.add("CLOSE_PAREN", r'\)')
    rply_lexer.add("OPEN_BRACKET", r'\[')
    rply_lexer.add("CLOSE_BRACKET", r'\]')

    rply_lexer.add("EXPRESSION_SEPARATOR", r',')

    rply_lexer.add("STATEMENT_SEPARATOR", r':')

    rply_lexer.ignore(r'\s+')

    return rply_lexer.build()

