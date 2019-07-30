import sys
from ast import literal_eval
from collections import deque


class ParseError(Exception):
    """Some parse error."""


class BaseValidator(object):
    
    def validate(self, expr):
        raise NotImplemented()


class OptValidator(BaseValidator):

    def __init__(self, validator):
        self.validator = validator

    def validate(self, expr):
        if expr:
            return self.validator.validate(expr)
        return True, None

    def __str__(self):
        return "?( " + str(self.validator) + " )"


class OrValidator(BaseValidator):
    
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def validate(self, expr):
        lv, le = self.left.validate(expr)
        if lv: return lv, None
        rv, re = self.right.validate(expr)
        if rv: return rv, None
        return " also ".join(le, re)

    def __str__(self):
        return str(self.left) + ' or ' + str(self.right)


class ValidateList(BaseValidator):
    
    def __init__(self, inner):
        self.inner = inner

    def validate(self, expr):
        print 'v:', expr, ' t:', type(expr)
        if not isinstance(expr, list):
            try:
                expr = literal_eval(expr)
            except ValueError:
                return None, "Cannot parse a list"

        if not isinstance(expr, list):
            return None, "This is not a list"
        if not self.inner:
            return l, None

        errors = []
        for item in expr:
            v, e = self.inner.validate(item)
            if not v:
                errors.append(e)
        if errors:
            return None, ', '.join(errors)
        return expr, None

    def __str__(self):
        return '[ ' + str(self.inner) + ' ]'


class ValidateInt(BaseValidator):

    def validate(self, expr):
        try:
            return int(expr), None
        except:
            return None, "Failed to validate int"

    def __str__(self):
        return 'int'


class ValidateFloat(BaseValidator):

    def validate(self, expr):
        try:
            return float(expr), None
        except:
            return None, "Failed to validate float"
        
    def __str__(self):
        return 'float'


class ValidateStr(BaseValidator):

    def validate(self, expr):
        try:
            return str(expr), None
        except:
            return None, "Failed to validate str"

    def __str__(self):
        return 'str'


# optional
OPT = '?'

# list
OSB = '['
CSB = ']'

# dict
OCB = '{'
CCB = '}'

# base types
FLOAT = 'float'
INT = 'int'
STR = 'str'

# logical OR
OR = 'or'


TYPES = (FLOAT, INT, STR)

TOKENS = sorted((OPT, OSB, CSB, OCB, CCB, FLOAT, INT, STR, OR), key=len, reverse=True)


def load_config(filename):
    """Load config and return config object"""
    try:
        from ConfigParser import ConfigParser
    except ImportError:
        from configparser import ConfigParser
    parser = ConfigParser()
    if not parser.read([filename]):
        sys.exit("Error reading %s" % (filename, ))
    return {'.'.join([section, key]):parser.get(section, key) for section in parser.sections() for key in parser.options(section)}


def tokenize(expr):
    expr = expr.lower().lstrip()
    tokens = deque()
    while expr:
        print 't:', tokens
        for token in TOKENS:
            print 'expr: ', expr, ' token: ', token
            if expr.startswith(token):
                tokens.append(token)
                expr = expr[len(token):].lstrip()
                break
        else:
            raise ParseError("unknown token: %s" % (expr, ))
    print 'tokens: ', tokens
    return tokens

def accept(tokens, token_type):
    if tokens and tokens[0] == token_type:
        return tokens.popleft()
    return None

def parse_simple(tokens):
    print 'ps tokens:', tokens
    token = accept(tokens, STR)
    if token:
        return ValidateStr()
    token = accept(tokens, INT)
    if token:
        return ValidateInt()
    token = accept(tokens, FLOAT)
    if token:
        return ValidateFloat()
    # try to parse the list
    token = accept(tokens, OSB)
    if token:
        inner = parse_base(tokens)
        print 'inner: ', inner
        if accept(tokens, CSB):
            return ValidateList(inner)
    return None

def parse_or(tokens):
    validators = deque()
    while True:
        or_ = accept(tokens, OR)
        if or_:
            or_validator = parse_simple(tokens)
            if not or_validator:
                raise ParseError("No expression after `or`")
            validators.append(or_validator)
        else:
            return validators

def parse_base(tokens):
    validator = parse_simple(tokens)
    if not validator:
        raise ParseError("Cannot parse type: %s" % (expr, ))

    or_validators = parse_or(tokens)
    while or_validators:
        validator = OrValidator(validator, or_validators.popleft())
    return validator

def parse_type(expr):
    tokens = tokenize(expr)

    optional = accept(tokens, OPT)
    validator = parse_base(tokens)

    if optional:
        validator = OptValidator(validator)
    return validator


def main():
    if len(sys.argv) != 3:
        sys.exit("Check args")
    base_conf = load_config(sys.argv[1])
    type_conf = load_config(sys.argv[2])
    for key in type_conf:
        constraint = parse_type(type_conf[key])
        print 'key: ', key, ' constraint: ', constraint
        r, e = constraint.validate(base_conf.get(key, None))
        if e:
            print 'key:', key, ' e: ', e
    print type_conf



if __name__ == "__main__":
    main()
