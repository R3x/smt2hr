import pysmt
from pysmt.smtlib.parser import SmtLibParser

def parse(fp):
    p = SmtLibParser()
    script = p.get_script(fp)
    ret = ""
    for asserts in script.filter_by_command_name(["assert"]): 
        ret += "assert :\t"
        ret += asserts.args[0].serialize()
        ret += "\n"
    return ret