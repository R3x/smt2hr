from __future__ import annotations

import re
import sys

from typing import List, Tuple, Any
from pysmt.smtlib.parser import SmtLibParser, SmtLibScript
from pysmt.environment import get_env

from more_itertools import peekable

class Stmt(object):

    def __init__(self, name, serialized):
        if not isinstance(name, str):
            if len(name) > 1:
                raise ValueError("Name should be a single one.")

            self.name = str(name[0])
        else:
            self.name = name

        self.serialized = serialized
        
        self.stmt = self.stmt_gen()
        
        self.tokens = self.tokenize()
        if len(self.tokens) == 1:
            self.tokens = self.tokens[0]

    def stmt_gen(self):
        for i in self.serialized:
            yield i

    def tokenize(self):
        curr_name = ""
        tokens = []
        while True:
            try:
                tok = next(self.stmt)
            except StopIteration:
                return tokens
            if tok == "(":
                sub_tokens = self.tokenize()
                if sub_tokens != []:
                    tokens.append(sub_tokens)
            elif tok == ")":
                if curr_name != "":
                    tokens.append(curr_name)
                return tokens
            elif tok == " ":
                if curr_name != "":
                    tokens.append(curr_name)
                curr_name = ""
            else:
                curr_name += tok
    
    def __str__(self):
        ret = "Name: " + self.name + "\n"
        ret += "Statement: " + self.serialized + "\n"
        return ret

class DeclStmt(Stmt):

    ignore_tokens_list = ["declare-fun"]

    def __init__(self, name, serialized):
        super().__init__(name, serialized)


    def parse_stmt(self):
        tname = ""
        ttype = ""
        for token in self.tokens:
            if isinstance(token, str):
                # if token can be ignored, ignore it
                # all smt2 tokens are ignored
                if token in self.ignore_tokens_list:
                    continue
                # if the token is the arg let's save it
                elif token == self.name:
                    tname = token
                else:
                    raise ValueError("Unexpected token: " + token)
            # Now, I have only seen Arrays usually
            # so I am ignoring the rest 
            elif isinstance(token, list):
                # if it's an array, it should have 2 elements
                if token[0] == "Array":
                    ttype = token[0]
        return tname, ttype

class AssertStmt(Stmt):
    
    ignore_tokens_list = ["assert"]

    def __init__(self, name, serialized):
        super().__init__(name, serialized)
        self.program_var_sizes = {}
        self.smt_vars = {}
        self.tokenizer = peekable(self.tokens)
        self.tokens = self.simplify_tokens(self.tokens)

    def simplify_tokens(self, tokens):
        new_tokens = []
        for token in tokens:
            if isinstance(token, list):
                if len(token) == 1 and isinstance(token[0], list):
                    token = token[0]
                new_tokens.append(self.simplify_tokens(token))
            else:
                new_tokens.append(token)
        return new_tokens



    def parse_stmt(self, tokens = None):
        token = tokens[1]
        while True:
            if isinstance(token, str):
                # if token can be ignored, ignore it
                # all smt2 tokens are ignored
                # if token in self.ignore_tokens_list:
                #     token = tokens[1] 
                #     continue
                if self.is_variable(token):
                    return self.smt_vars[token]
                # if the token is the arg let's save it
                else:
                    raise ValueError("Unexpected token: " + token)
            # Now, I have only seen Arrays usually
            # so I am ignoring the rest 
            elif isinstance(token, list):
                # if it's an array, it should have 2 elements
                type_tok = token[0]
                if type_tok == "let":
                    assert(isinstance(token[1], list) == True)
                    assert(len(token[1]) == 2)
                    let_token = token[1]
                    expr = self.parse_expr(let_token[1])
                    self.smt_vars[let_token[0]] = expr
                    token = token[2:]
                elif isinstance(token, list):
                    token = token[0]
                else:
                    raise ValueError(f"Unexpected token: {token}")

    def parse_expr(self, tokens):
        if isinstance(tokens, list):
            if isinstance(tokens[0], str):
                # unpacking
                if len(tokens) == 3:
                    func, arg1, arg2 = tokens
                else:
                    func, arg1, arg2 = tokens[0], tokens[1], tokens[2:]
                
                # operations
                if func == "select":
                    # ['select', 'foo_arg_1', '#b00000000000000000000000000000000']
                    self.program_var_sizes[arg1] = self.predict_size(arg2)
                    return arg1
                elif func == "concat":
                    # ['.def_21', ['concat', '.def_20', '.def_19']]
                    arg1_var = self.smt_vars[arg1]
                    arg2_var = self.smt_vars[arg2]
                    if arg1_var == arg2_var:
                        return arg1_var
                    else:
                        raise ValueError("Concatenation of different variables")
                elif func == "_":
                    # ['_', 'sign_extend', '32']
                    if arg1 == "sign_extend":
                        return {"operation" : "sign_extend", "size" : int(arg2)}
                    elif arg1 == "extract":
                        return {"operation" : "extract", "start" : int(arg2[0]), "end" : int(arg2[1])}
                    else:
                        raise ValueError("Unknown operation: " + arg1)
                elif func == "bvmul":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} * {arg2}"
                elif func == "=":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} == {arg2}"
                elif func == "bvslt":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} < {arg2}"
                elif func == "bvurem":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} % {arg2}"
                elif func == "bvadd":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} + {arg2}"
                elif func == "bvsub":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} - {arg2}" 
                elif func == "and":
                    arg1 = self.get_value(arg1)
                    arg2 = self.get_value(arg2)
                    return f"{arg1} and {arg2}"
                else:
                    raise ValueError("Unknown operation: " + func)
            if isinstance(tokens[0], list):
                var = self.parse_expr(tokens[0])
                if isinstance(var, dict) and var["operation"] == "sign_extend":
                    arg_var = self.smt_vars[tokens[1]]
                    return f"(int{var['size']})({arg_var})"
                elif isinstance(var, dict) and var["operation"] == "extract":
                    arg_var = self.smt_vars[tokens[1]]
                    if var['end'] == 0:
                        return f"(int{var['start'] + 1 })({arg_var})"
                    else:
                        raise ValueError(f"Extracting from middle of variable {var}")
                else:
                    raise ValueError(f"Unknown result of operation: {tokens[0]} : {var} ")
        else:
            raise ValueError("Unexpected token strings: " + tokens)

    def predict_size(self, arg2):
        # need to parse the bitvector, get the top 1 to find the size
        return 32

    def get_value(self, name):
        if self.is_variable(name):
            return self.smt_vars[name]
        else:
            if self.is_bitvector(name):
                return int(name.replace("#b", ""), 2)

    def is_variable(self, name):
        if name.startswith(".def"):
            return True
        return False

    def is_bitvector(self, name):
        if name.startswith("#b"):
            return True
        return False

def parse_one_file(filename : str):
    """
        Parse one file and return the parsed script.
    :param filename: File path.
    :return: Parsed script.
    """
    with open(filename, "r") as fp:
        p = SmtLibParser()
        script = p.get_script(fp)

        parse_declares(script.filter_by_command_name(["declare-fun"]))
        parse_asserts(script.filter_by_command_name(["assert"]))
    print("Done Parsing")

def parse_declares(stmts):
    for stmt in stmts:
        dstmt = DeclStmt(stmt.args, stmt.serialize_to_string())
        print(dstmt.parse_stmt())

def parse_asserts(stmts):
    for stmt in stmts:
        astmt = AssertStmt("ASSERT", stmt.serialize_to_string())
        val = astmt.parse_stmt(astmt.tokens)
        print(val)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 smt2inf.py <smt2 file>")
        sys.exit(1)
    get_env().enable_infix_notation = True
    parse_one_file(sys.argv[1])
