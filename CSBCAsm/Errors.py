
class BuildError(Exception):
    pass

class LabelRedefinitionError(Exception):
    pass

class ReservedNameError(Exception):
    pass

class InvalidNameError(Exception):
    pass

class SegmentRedefinitionError(Exception):
    pass

class NoSegmentError(Exception):
    pass

class EquateDefinitionError(Exception):
    pass

class InvalidStatementError(Exception):
    pass

class IncorrectParameterCountError(Exception):
    pass

class InvalidParameterError(Exception):
    pass

class FeatureNotImplementedError(Exception):
    pass

class SegmentOverflowError(Exception):
    pass

class UnknownOpcodeError(Exception):
    pass

class UnknownAddressingModeError(Exception):
    pass

class InvalidStatementError(Exception):
    pass

class RelativeBranchOutOfRangeError(Exception):
    pass

class ParameterTooLargeError(Exception):
    pass

class GlobalRedefinitionError(Exception):
    pass

class InvalidGlobalError(Exception):
    pass

class UndefinedLabelError(Exception):
    pass

class UnknownCompilerDirectiveError(Exception):
    pass

class NameNotEvaluatableError(Exception):
    def __init__(self, message, name):
        self.name = name
        super().__init__(message)

class UnmatchedEndIfError(Exception):
    pass

class UnexpectedFlowControlError(Exception):
    pass

class ParameterSizeError(Exception):
    pass

class MacroError(Exception):
    pass

class MissingMacroLabelError(Exception):
    pass

class ElipsesNotValidError(Exception):
    pass

class FileNotFoundError(Exception):
    pass

