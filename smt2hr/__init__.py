from .simplify import parse as simplifier

def parse(fp, pretty):
    return simplifier(fp, pretty)