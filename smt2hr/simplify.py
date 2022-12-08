import pysmt
import re
from pysmt.smtlib.parser import SmtLibParser

def parse(fp):
    p = SmtLibParser()
    script = p.get_script(fp)
    ret = ""
    for asserts in script.filter_by_command_name(["assert"]): 
        # ret += "assert :\t"
        # ret += asserts.args[0].serialize()
        # ret += "\n"
        # print("-----------------")
        # print(asserts.args[0].serialize())
        # print("-----------------")
        tokens = Tokenizer(asserts.args[0].serialize())
        ret += tokens.tokens_to_string()
        ret += '\n\n'
    return ret[:-2]

OPERATORS = ['&', '<', '>', 's<', 's>', '%', 'u%']

'''
(((5_32 = ((foo_arg_0_dynSize[3_32]::(foo_arg_0_dynSize[2_32]::(foo_arg_0_dynSize[1_32]::foo_arg_0_dynSize[0_32]))) u% 129_32)) & ((foo_arg_1[3_32]::(foo_arg_1[2_32]::(foo_arg_1[1_32]::foo_arg_1[0_32]))) s< (foo_arg_2[3_32]::(foo_arg_2[2_32]::(foo_arg_2[1_32]::foo_arg_2[0_32]))))) & (131068_32 = (4_64 * ((foo_arg_1[3_32]::(foo_arg_1[2_32]::(foo_arg_1[1_32]::foo_arg_1[0_32]))) SEXT 32))[0:31]))

We need to tokenize this string into a list of tokens, that we can parse into a tree and then modify and simplify.
'''

class Tokenizer():

    def __init__(self, string):
        self.string = string
        self.tokens = []
        self.token = ""
        self.in_string = False
        self.in_token = False
        self.in_paren = False
        self.paren_count = 0
        self.tokenize()
        self.remove_bit_width_from_tokens()
        self.concatnating_arrays()
        self.remove_uneeded_parens()

    def tokenize(self):
        for char in self.string:
            if char == "(":
                # self.in_paren = True
                # self.paren_count += 1
                if self.in_token:
                    self.tokens.append(self.token)
                    self.token = ""
                    self.in_token = False
                self.tokens.append(char)
            elif char == ")":
                # self.paren_count -= 1
                # if self.paren_count == 0:
                #     self.in_paren = False
                if self.in_token:
                    self.tokens.append(self.token)
                    self.token = ""
                    self.in_token = False
                self.tokens.append(char)
            elif char == " ":
                if self.in_token:
                    self.tokens.append(self.token)
                    self.token = ""
                    self.in_token = False
                else:
                    self.in_token = True
                    self.token += char
            else:
                self.token += char
                self.in_token = True
        #print(self.tokens)

    def remove_bit_width_from_tokens(self):
        '''
        Iterate through all the tokens, if a token contains a bit width (e.g. 10_32), make it 10. 
        '''

        BITWIDTHS = ["1", "8", "16", "32", "64", "128", "256"]
        for i in range(len(self.tokens)):
            if self.tokens[i] == "(" or self.tokens[i] == ")" or self.tokens[i] in OPERATORS:
                continue
            # Let's check if the token is in the form of 10_32 without any spaces
            # using regex
            if re.match(r"^\d+_\d+$", self.tokens[i]):
                # Split the token into two parts, the number and the bit width
                token_parts = self.tokens[i].split("_")
                # Check if the bit width is in the list of bit widths
                if token_parts[1] in BITWIDTHS:
                    # Replace the token with the number
                    self.tokens[i] = token_parts[0]
            
            # Find all places in the token where the string '[10_32]' is present and replace it with '[10]'
            # using regex
            if re.search(r"\[\d+_\d+\]", self.tokens[i]):
                # Find all the matches
                matches = re.findall(r"\[\d+_\d+\]", self.tokens[i])
                for match in matches:
                    # Split the match into two parts, the number and the bit width
                    match_parts = match.split("_")
                    # Check if the bit width is in the list of bit widths
                    if match_parts[1][:-1] in BITWIDTHS:
                        # Replace the match with the number
                        self.tokens[i] = self.tokens[i].replace(match, match_parts[0] + "]")

    def concatnating_arrays(self):
        '''
        We iterate through the tokens, and if we find a set of tokens that looks like this:
        ['(', 'foo_arg_0_dynSize[3_32]::', '(', 'foo_arg_0_dynSize[2_32]::', '(', 'foo_arg_0_dynSize[1_32]::foo_arg_0_dynSize[0_32]', ')', ')', ')']

        it needs to be replaced with a single token
        ['foo_arg_0_dynSize[3:0]']
        '''
        NROUNDS = 20
        for rnd in range(NROUNDS):
            # Let's first reduce any token with a '::' in the middle
            for i in range(len(self.tokens) - 1):
                if i > len(self.tokens) - 1:
                    break
                if self.tokens[i] == "(" or self.tokens[i] == ")" or self.tokens[i] in OPERATORS:
                    continue
                if "::" in self.tokens[i]:
                    split_tokens = self.tokens[i].split("::")
                    if len(split_tokens[-1]) != 0:
                        """
                        Handling the case where the token is of the form
                        foo_arg_0_dynSize[3_32]::foo_arg_0_dynSize[2_32]::foo_arg_0_dynSize[1_32]::foo_arg_0_dynSize[0_32]
                        """
                        #print("split_tokens: ", split_tokens) 
                        replace = False
                        first_idx = -1
                        last_idx = -1
                        name = ""
                        for j in range(len(split_tokens) - 1):
                            # Check if the current split and then next split are in the form of
                            # foo_arg_0[1] or foo_arg_0[2]
                            first = re.match(r"^([\w'->.:]+)\[(\d+)[\d:]*?\]$", split_tokens[j])
                            second = re.match(r"^([\w'->.:]+)\[[\d:]*?(\d+)\]$", split_tokens[j+1])
                            if first and second:
                                if first.group(1) == second.group(1):
                                    replace = True
                                    name = first.group(1)
                                    if first_idx == -1:
                                        first_idx = int(first.group(2))
                                    last_idx = int(second.group(2))
                                else:
                                    replace = False
                                    break
                        if replace:
                            #print(f"Replacing {self.tokens[i]} with {name}[{first_idx}:{last_idx}]")
                            self.tokens[i] = name + "[" + str(first_idx) + ":" + str(last_idx) + "]"
                    else:
                        """
                        Handling the case where the token is of the form
                        'foo_arg_0_dynSize[3_32]::foo_arg_0_dynSize[2_32]::', '(', 'foo_arg_0_dynSize[1_32]::foo_arg_0_dynSize[0_32]', ')'
                        """
                        # Let's check if there are 3 more tokens after this
                        if i + 3 > len(self.tokens):
                            continue

                        # Let's check if the next 3 tokens are of the form
                        # '(', 'foo_arg_0_dynSize[1_32]::foo_arg_0_dynSize[0_32]', ')'
                        if self.tokens[i+1] != "(" or self.tokens[i+3] != ")":
                            continue

                        self.tokens[i] = self.tokens[i] + self.tokens[i+2]
                        del self.tokens[i+1]
                        del self.tokens[i+1]
                        del self.tokens[i+1]

    def remove_uneeded_parens(self):
        '''
        If there are tokens of the form
        ['(' 'foo_arg_0_dynSize[3_32]' ')']

        we need to delete the first and last token
        '''
        for i in range(len(self.tokens) - 1):
            if i > len(self.tokens) - 1:
                break
            if self.tokens[i] == "(" and self.tokens[i+2] == ")":
                del self.tokens[i]
                del self.tokens[i+1]

    def tokens_to_string(self):
        ret = ""
        for i in range(len(self.tokens)):
            if self.tokens[i] == "(" or self.tokens[i] == ")":
                ret += self.tokens[i]
            elif self.tokens[i - 1] == "(" or self.tokens[i - 1] == ")":
                ret += self.tokens[i]
            else:
                ret += " " + self.tokens[i]
        return ret

def remove_bit_width(data):
    return tokens.tokens_to_string()