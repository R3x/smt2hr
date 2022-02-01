from __future__ import annotations

import re
import sys

from typing import List, Tuple, Any
from pysmt.smtlib.parser import SmtLibParser, SmtLibScript
from pysmt.environment import get_env

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

    def parse_stmt(self):
        substmts = []
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
        print(astmt.parse_stmt())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 smt2inf.py <smt2 file>")
        sys.exit(1)
    get_env().enable_infix_notation = True
    parse_one_file(sys.argv[1])
