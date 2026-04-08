from re import findall

'''Processes DTAs and turns them into native Python data collections, and vice versa'''

def tokenize(dta: str):
    return findall(r'\'[^\']*\'|\"[^\"]*\"|\(|\)|;[^\n]*|[^\s()]+', dta)

def parse_tokens(tokens, i=0):
    parsed = []
    while i < len(tokens):
        token = tokens[i]

        if token == '(':
            i, subtree = parse_tokens(tokens, i + 1)
            parsed.append(subtree)
        elif token == ')':
            return i, parsed
        elif token.startswith(';'):
            pass
        else:
            parsed_atom = parse_atom(token)
            parsed.append(parsed_atom)
        i += 1
    return i, parsed

def parse_atom(token):
    if token.startswith("\'") and token.endswith("\'"):
        return token[1:-1]
    if token.upper() == 'TRUE':
        return True
    if token.upper() == 'FALSE':
        return False
    try:
        if '.' in token:
            return float(token)
        elif token.isdecimal() or (token[0] == '-' and token[1:].isdecimal()):
            return int(token)
        else:
            return token
    except ValueError:
        return token

def dta_to_nested_list(dta):
    tokens = tokenize(dta)
    _, parsed = parse_tokens(tokens)
    return parsed

def nested_list_to_dta(nested,level=1,indent="   "):
    s = ""
    if isinstance(nested, list):
        s = "("
        if any(isinstance(each,list) for each in nested):
            for i,each in enumerate(nested):
                s += "\n"+(indent*level) + (nested_list_to_dta(each,level+1) + " " if i != len(nested)-1 else nested_list_to_dta(each,level+1))
            s += "\n"+(indent*(level-1))+")"
        else:
            for i,each in enumerate(nested):
                s += (nested_list_to_dta(each, level) + " ") if i != len(nested)-1 else nested_list_to_dta(each,level)
            s += ")"
    else:
        s = str(nested)
    return s

def __nested_list_to_dict__(nest:list):
    if len(nest) == 2:
        if all(isinstance(item, str) for item in nest) or (isinstance(nest[0],str) and (isinstance(nest[1], int) or isinstance(nest[1], float))):
            k= nest[0]
            v = nest[1]
            return {k:v}
        elif all(isinstance(item, str) for item in nest) or all(isinstance(item, int) for item in nest) or all(isinstance(item, float) for item in nest):
            return nest
        
        elif isinstance(nest[0], str) and isinstance(nest[1], list):
            k = nest[0]
            v = __nested_list_to_dict__(nest[1])
            return {k:v}
        
        elif isinstance(nest[0], str) and all(isinstance(item, list) for item in nest[1]):
            k = nest[0]
            v = [__nested_list_to_dict__(item) for item in nest[1:]]
            return {k:v}
    else:
        if isinstance(nest[0], str) and all(isinstance(item,list) for item in nest[1:]):
            k = nest[0]
            v = [__nested_list_to_dict__(item) for item in nest[1:]]
            return {k:v}
        elif all(isinstance(item, list) for item in nest):
            return [__nested_list_to_dict__(item) for item in nest]
        elif all(isinstance(item, str) for item in nest) or all(isinstance(item, int) for item in nest) or all(isinstance(item, float) for item in nest):
            return nest
        else:
            return nest

def __dict_to_nested_list__(dta_dict):
    if isinstance(dta_dict, list) and all(isinstance(item,dict) for item in dta_dict):
        return [__dict_to_nested_list__(item) for item in dta_dict]
    elif isinstance(dta_dict, dict):
        if len(dta_dict.items()) == 1:
            dict_list = list(list(dta_dict.items())[0])
            if isinstance(dict_list[1], list):
                keyed_nest = [dict_list[0]] + [[__dict_to_nested_list__(item) for item in dict_list[1]]]
                return keyed_nest
            else:
                return dict_list
    else:
        return dta_dict