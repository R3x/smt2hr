from .simplify import parse as simplifier

def parse(fp):
    return simplifier(fp)