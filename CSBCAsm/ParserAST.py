import math

from .Errors import *

class Number():
    def __init__(self, value, base, stated_byte_size):
        self.value = value
        self.base = base

        # Stated byte size is the size stated by the program or any effect the programmer
        # caused to be true;  "0x1000" is stated as 2 bytes, and so is 0x0011.  10+0xFF
        # is stated as two 1 byte numbers but will add to be a two byte number.
        # some operations like bitwise AND can reduce the number of bytes required
        # 0x1234 & 0xFF will result in a 1 byte number
        self.stated_byte_size = stated_byte_size

    def find_referenced_names(self, search_results=None):
        # No names here, buddy!
        return search_results

    def guess_size(self):
        return self.stated_byte_size

    def collapse(self, drop_overflow_bytes=False):
        '''Like eval(), but return a Number(), trying to determine byte sizes along the way'''
        return Number(self.value, self.base, self.stated_byte_size)

    def eval(self):
        return self.value

    def as_segment_address(self):
        v = self.eval()
        return "{:02X}:{:04X}".format((v >> 16) & 0xFF, v & 0xFFFF)

    @staticmethod
    def required_bytes(v):
        if v < 0:
            # Pretty hacky..
            nbytes = 1
            while True:
                try:
                    v.to_bytes(nbytes, 'little', signed=True)
                    return nbytes
                except OverflowError:
                    # Number too big to fit in 'i' bytes
                    nbytes = nbytes + 1
                    continue
        elif v == 0 or v == 1:
            return 1
        else:
            nbits = math.floor(math.log2(v)) + 1
            return (nbits + 7) // 8

    def __str__(self):
        if self.base == 'dec':
            return "<Number:{} size:{}>".format(self.value, self.stated_byte_size)
        elif self.base == 'hex':
            hex_fmt = "{:0" + str(self.stated_byte_size * 2) + "X}"
            return ("<Number:0x" + hex_fmt + " size:{}>").format(self.value, self.stated_byte_size)
        elif self.base == 'bin':
            bin_fmt = "{:0" + str(self.stated_byte_size * 2) + "b}"
            return ("<Number:0x" + bin_fmt + " size:{}>").format(self.value, self.stated_byte_size)
        else:
            raise NotImplementedError()

class Immediate():
    def __init__(self, value):
        self.value = value

    def find_referenced_names(self, search_results=None):
        return self.value.find_referenced_names(search_results)

    def __str__(self):
        return "<Immediate:{}>".format(str(self.value))

class Name():
    def __init__(self, value, line, column, as_long=False):
        self.value = value
        self.line = line
        self.column = column
        self.actual_value = None
        self.as_long = as_long

    def guess_size(self):
        if self.actual_value is not None:
            s = self.actual_value.guess_size()
            if self.as_long:
                if s > 3:
                    return s
                return 3
            return s
        return 3 if self.as_long else 2

    def set_actual_value(self, actual_value):
        if self.actual_value is not None:
            assert self.actual_value.eval() == actual_value.eval()
        self.actual_value = actual_value

    def find_referenced_names(self, search_results=None):
        if search_results is None:
            search_results = {}
        if self.value in search_results:
            search_results[self.value].append(self)
        else:
            search_results[self.value] = [self]
        if self.actual_value is not None:
            search_results = self.actual_value.find_referenced_names(search_results)
        return search_results

    def collapse(self, drop_overflow_bytes=False):
        '''Like eval(), but return a Number(), trying to determine byte sizes along the way'''
        if self.actual_value is None:
            raise NameNotEvaluatableError("Cannot collapse name: {}".format(self.value), self)
        return self.actual_value.collapse(drop_overflow_bytes=drop_overflow_bytes)

    def eval(self):
        if self.actual_value is None:
            raise NameNotEvaluatableError("Cannot evaluate name: {}".format(self.value), self)
        return self.actual_value.eval()

    def __str__(self):
        return "<Name:{}>".format(self.value)

    def __eq__(self, other):
        return self.value == other.value and self.line == other.line and self.column == other.column

class QuotedString():
    def __init__(self, value, petscii=False):
        self.value = value
        self.petscii = petscii

    def find_referenced_names(self, search_results=None):
        # No names here, buddy!
        return search_results

    def __str__(self):
        return "<QuotedString:{}>".format(self.value)

class ExpressionList():
    def __init__(self):
        self.value = []
        self.long = False

    def guess_size(self):
        if len(self.value) == 1:
            return self.value[0].guess_size()
        raise ParameterSizeError("Cannot determine size to argument")

    def append_expression(self, value):
        self.value.append(value)

    def find_referenced_names(self, search_results=None):
        for v in self.value:
            search_results = v.find_referenced_names(search_results)
        return search_results

    def collapse(self, drop_overflow_bytes=False):
        '''Like eval(), but return a Number(), trying to determine byte sizes along the way'''
        if len(self.value) == 1:
            return self.value[0].collapse(drop_overflow_bytes=drop_overflow_bytes)
        return [v.collapse(drop_overflow_bytes=drop_overflow_bytes) for v in self.value]

    def eval(self):
        if len(self.value) == 1:
            return self.value[0].eval()
        return [v.eval() for v in self.value]

    def __str__(self):
        return "<ExpressionList:[{}]>".format(', '.join([str(v) for v in self.value]))

class Statement():
    def __init__(self, name, operands, has_elipses=False):
        self.name = name
        self.operands = operands
        self.has_elipses = has_elipses

    def __str__(self):
        return "<Statement:{} {}>".format(str(self.name), str(self.operands))

class StatementList():
    def __init__(self):
        self.value = []

    def pop_first(self):
        self.value = self.value[1:]

    def append_statement(self, statement):
        self.value.append(statement)

    def __str__(self):
        return "<Statements:[{}]>".format(','.join([str(x) for x in self.value]))

class Line():
    def __init__(self, statement_list=None, label_declaration=None, equate=None):
        if statement_list is None:
            statement_list = StatementList()
        self.statement_list = statement_list
        self.label_declaration = label_declaration
        self.equate = equate
        self.line_number = None
        assert self.equate is None or len(self.statement_list.value) == 0

    def __str__(self):
        lblstr = ""
        if self.label_declaration is not None:
            lblstr = " " + str(self.label_declaration)
        return "<Line:{} {}>".format(str(self.statement_list), lblstr)

class Equate():
    def __init__(self, name, expression):
        self.name = name
        self.expression = expression
        self.final = False

class UnaryOp():
    def __init__(self, value):
        self.value = value

    def find_referenced_names(self, search_results=None):
        return self.value.find_referenced_names(search_results)

class UnaryOp_Negate(UnaryOp):
    def guess_size(self):
        return self.value.guess_size()

    def collapse(self, drop_overflow_bytes=False):
        c = self.value.collapse(drop_overflow_bytes=drop_overflow_bytes)
        # negating shouldn't change the byte size
        n = Number(-c.value, c.base, c.stated_byte_size)
        return n

    def eval(self):
        return -self.value.eval()

class UnaryOp_Posigate(UnaryOp):
    def collapse(self, drop_overflow_bytes=False):
        c = self.value.collapse(drop_overflow_bytes=drop_overflow_bytes)
        # posigating shouldn't change the byte size
        n = Number(+c.value, c.base, c.stated_byte_size)
        return n

    def eval(self):
        return +self.value.eval()

class UnaryOp_Not(UnaryOp):
    def guess_size(self):
        return self.value.guess_size()

    def collapse(self, drop_overflow_bytes=False):
        c = self.value.collapse(drop_overflow_bytes=drop_overflow_bytes)
        nv = (1 << (c.stated_byte_size * 8)) - 1 - c.eval()
        n = Number(nv, c.base, c.stated_byte_size)
        return n

    def eval(self):
        # Python rolls with signed ints, so this negates the input. In assembly, we don't want that.
        # TODO: I think I'm going to find that stated_byte_size/typed_byte_size will need
        # to be part of Expression(), not Number(), which is of course an expression.
        v = self.value.collapse()
        return (1 << (v.stated_byte_size * 8)) - 1 - v.eval()

class UnaryOp_LowByte(UnaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        c = self.value.collapse(drop_overflow_bytes=drop_overflow_bytes)
        n = Number(c.eval() & 0xFF, c.base, 1)
        return n

    def eval(self):
        return self.value.eval() & 0xFF

class UnaryOp_HighByte(UnaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        c = self.value.collapse(drop_overflow_bytes=drop_overflow_bytes)
        n = Number((c.eval() >> 8) & 0xFF, c.base, 1)
        return n

    def eval(self):
        return (self.value.eval() >> 8) & 0xFF

class UnaryOp_LogicalNot(UnaryOp):
    def collapse(self, drop_overflow_bytes=False):
        c = self.value.collapse(drop_overflow_bytes=drop_overflow_bytes).eval()
        return ParserAST.Number(int(not c.eval()), 'dec', 1)

    def eval(self):
        return int(not self.value.eval())

class BinaryOp():
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def find_referenced_names(self, search_results=None):
        search_results = self.left.find_referenced_names(search_results)
        return self.right.find_referenced_names(search_results)

    def _collapse_common(self, opfunc, drop_overflow_bytes=False, can_shrink=False):
        left = self.left.collapse(drop_overflow_bytes=drop_overflow_bytes)
        right = self.right.collapse(drop_overflow_bytes=drop_overflow_bytes)
        nv = opfunc(left.eval(), right.eval())

        bigger_stated_size = max(left.stated_byte_size, right.stated_byte_size)

        if drop_overflow_bytes:
            new_stated_byte_size = max(left.stated_byte_size, right.stated_byte_size)
            nv = nv & ((1 << (new_stated_byte_size * 8)) - 1)
        else:
            new_stated_byte_size = max(Number.required_bytes(nv), bigger_stated_size)

        if can_shrink:
            new_stated_byte_size = Number.required_bytes(nv)

        new_base = left.base # left expression gets precedence on base, for the lulz
        return Number(nv, new_base, new_stated_byte_size)

class BinaryOp_EqualTo(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int(l==r), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int(self.left.eval() == self.right.eval())

    def __str__(self):
        return "<BinaryOp_EqualTo:{}=={}>".format(str(self.left), str(self.right))

class BinaryOp_NotEqualTo(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int(l!=r), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int(self.left.eval() != self.right.eval())

    def __str__(self):
        return "<BinaryOp_NotEqualTo:{}!={}>".format(str(self.left), str(self.right))

class BinaryOp_LessThan(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int(l<r), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int(self.left.eval() < self.right.eval())

    def __str__(self):
        return "<BinaryOp_LessThan:{}<{}>".format(str(self.left), str(self.right))

class BinaryOp_GreaterThan(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int(l>r), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int(self.left.eval() > self.right.eval())

    def __str__(self):
        return "<BinaryOp_GreaterThan:{}>{}>".format(str(self.left), str(self.right))

class BinaryOp_LessThanOrEqualTo(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int(l<=r), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int(self.left.eval() <= self.right.eval())

    def __str__(self):
        return "<BinaryOp_LessThanOrEqualTo:{}<={}>".format(str(self.left), str(self.right))

class BinaryOp_GreaterThanOrEqualTo(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int(l>=r), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int(self.left.eval() >= self.right.eval())

    def __str__(self):
        return "<BinaryOp_GreaterThanOrEqualTo:{}>={}>".format(str(self.left), str(self.right))

class BinaryOp_LogicalOr(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int((not not l) or (not not r)), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int((not not self.left.eval()) or (not not self.right.eval()))

    def __str__(self):
        return "<BinaryOp_LogicalOr:{}||{}>".format(str(self.left), str(self.right))

class BinaryOp_LogicalAnd(BinaryOp):
    def guess_size(self):
        return 1

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: int((not not l) and (not not r)), drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return int((not not self.left.eval()) and (not not self.right.eval()))

    def __str__(self):
        return "<BinaryOp_LogicalAnd:{}&&{}>".format(str(self.left), str(self.right))


class BinaryOp_Add(BinaryOp):
    def guess_size(self):
        try:
            v = self.collapse()
            return v.stated_byte_size
        except:
            return max(self.left.guess_size(), self.right.guess_size())

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l+r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() + self.right.eval()

    def __str__(self):
        return "<BinaryOp_Add:{}+{}>".format(str(self.left), str(self.right))

class BinaryOp_Sub(BinaryOp):
    def guess_size(self):
        try:
            v = self.collapse()
            return v.stated_byte_size
        except:
            return max(self.left.guess_size(), self.right.guess_size())

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l-r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() - self.right.eval()

    def __str__(self):
        return "<BinaryOp_Sub:{}-{}>".format(str(self.left), str(self.right))

class BinaryOp_Mul(BinaryOp):
    def guess_size(self):
        try:
            v = self.collapse()
            return v.stated_byte_size
        except:
            return max(self.left.guess_size(), self.right.guess_size())

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l*r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() * self.right.eval()

    def __str__(self):
        return "<BinaryOp_Mul:{}*{}>".format(str(self.left), str(self.right))

class BinaryOp_Div(BinaryOp):
    def guess_size(self):
        try:
            v = self.collapse()
            return v.stated_byte_size
        except:
            return self.left.guess_size()

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l//r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    # TODO: float and int support
    def eval(self):
        return self.left.eval() // self.right.eval()

    def __str__(self):
        return "<BinaryOp_Div:{}/{}>".format(str(self.left), str(self.right))

class BinaryOp_Pow(BinaryOp):
    def guess_size(self):
        try:
            v = self.collapse()
            return v.stated_byte_size
        except:
            return max(self.left.guess_size(), self.right.guess_size())

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l**r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() ** self.right.eval()

    def __str__(self):
        return "<BinaryOp_Pow:{}**{}>".format(str(self.left), str(self.right))

class BinaryOp_Mod(BinaryOp):
    def guess_size(self):
        try:
            v = BinaryOp_Sub(self.right.collapse(), Number(1, 'dec', 1))
            return v.stated_byte_size
        except:
            return self.left.guess_size()

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l%r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() % self.right.eval()

    def __str__(self):
        return "<BinaryOp_Mod:{}%{}>".format(str(self.left), str(self.right))

class BinaryOp_And(BinaryOp):
    def guess_size(self, drop_overflow_bytes=False):
        left_size = self.left.guess_size()
        right_size = self.right.guess_size()
        return min(left_size, right_size) # If you specify fewer bytes, ANDing the higher bytes with 0 can reduce the length of the data

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l&r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=True)

    def eval(self):
        return self.left.eval() & self.right.eval()

    def __str__(self):
        return "<BinaryOp_And:{}&{}>".format(str(self.left), str(self.right))

class BinaryOp_Xor(BinaryOp):
    def guess_size(self, drop_overflow_bytes=False):
        left_size = self.left.guess_size()
        right_size = self.right.guess_size()
        return max(left_size, right_size)

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l^r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() ^ self.right.eval()

    def __str__(self):
        return "<BinaryOp_Xor:{}^{}>".format(str(self.left), str(self.right))

class BinaryOp_Or(BinaryOp):
    def guess_size(self, drop_overflow_bytes=False):
        left_size = self.left.guess_size()
        right_size = self.right.guess_size()
        return max(left_size, right_size)

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l|r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() | self.right.eval()

    def __str__(self):
        return "<BinaryOp_Or:{}|{}>".format(str(self.left), str(self.right))

class BinaryOp_LeftShift(BinaryOp):
    def guess_size(self):
        mysize = self.left.guess_size()
        try:
            n = self.right.collapse().eval()
            return mysize + math.ceil(n / 8)
        except:
            return mysize

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l<<r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=False)

    def eval(self):
        return self.left.eval() << self.right.eval()

    def __str__(self):
        return "<BinaryOp_LeftShift:{}<<{}>".format(str(self.left), str(self.right))

class BinaryOp_RightShift(BinaryOp):
    def guess_size(self):
        mysize = self.left.guess_size()
        try:
            n = self.right.collapse().eval()
            return max(mysize - (n // 8), 1)
        except:
            return mysize

    def collapse(self, drop_overflow_bytes=False):
        return self._collapse_common(opfunc=lambda l, r: l>>r, drop_overflow_bytes=drop_overflow_bytes, can_shrink=True)

    def eval(self):
        return self.left.eval() >> self.right.eval()

    def __str__(self):
        return "<BinaryOp_RightShift:{}>>{}>".format(str(self.left), str(self.right))

