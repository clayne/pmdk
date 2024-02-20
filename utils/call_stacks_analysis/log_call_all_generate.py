#!/usr/bin/env python3

# SPDX-License-Identifier: BSD-3-Clause
# Copyright 2024, Intel Corporation

import subprocess
import json
import re

from typing import List, Dict, Any

DEBUG = False
PARSER_DEBUG = False

TOP = '../../src/'
OUTPUT_PATH = TOP + 'test/core_log_max/'
OUTPUT_C = OUTPUT_PATH + 'call_all.c.generated'

NOTICE = """/*
 * This file is automatically generated by utils/call_stack_analysis/log_call_all_generate.py.
 * Please do not modify manually.
 */"""

C_FUNCTION_W_ERRNUM_PREFIX = """
void
call_all_{}(int errnum)
{{
	errno = errnum;
"""

C_FUNCTION_PREFIX = """
void
call_all_{}(void)
{{
"""

C_FUNCTION_SUFFIX = """}
"""

def dump(var: Any, name: str) -> None:
    with open(f'{name}.json', 'w') as outfile:
        json.dump(var, outfile, indent = 4)

def bad_line(reason: str, line: str) -> None:
    print(f'{reason}: {line}')
    exit(1)

# Extract all calls from the code base

def extract_append_code(file_name: str, start_line: int, code: str) -> str:
    if not re.search(f'\.[ch]$', file_name):
        print(f'Unsupported file type: {file_name}')
        exit(1)

    with open(TOP + file_name, 'r') as file:
        # skip to the line
        for _ in range(0, start_line):
            file.readline()
        # look up for the end of the statement
        while True:
            line = file.readline()
            line = line.strip()
            code += " " + line
            if code[-1] == ';':
                break
            if re.search(f'(//|/\*)', code):
                bad_line('Comment found', code)
    return code

IGNORE_FILES = [
    'core/log_internal.h',
    'libpmem2/',
    'libpmempool/',
    'test/',
]

def file_should_be_ignored(file: str) -> bool:
    for ignore in IGNORE_FILES:
        if file.startswith(ignore):
            return True
    return False

def extract_all_calls(func: str) -> List[Dict]:
    returned_output = subprocess.check_output(['grep', '-Irn', func], cwd=TOP)
    string = returned_output.decode("utf-8")
    calls = []
    total = 0
    for line in string.splitlines():
        found = re.search(f'([a-zA-Z0-9_/.-]+):([0-9]+):[ \t]*(.+)', line)
        if found:
            total += 1
            file = found.group(1)
            line_no = found.group(2)
            code = found.group(3)
            # Filter out known odd occurrences.
            if file_should_be_ignored(file):
                continue
            if not code.startswith(func):
                bad_line(f'Does not start with "{func}"', line)
            if code[-1] == '\\': # template's type of ending a line
                if code[-2] == ';': # a single line call can be extracted
                    code = code[:-1]
                else:
                    print(f'SKIP call: Multiline calls in templates are not supported: {line}')
                    continue
            elif code[-1] != ';':
                code = extract_append_code(file, int(line_no), code)
            call = {
                'file': file,
                'line': line_no,
                'code': code
            }
            calls.append(call)
        else:
            bad_line('An unexpected line format', line)
    # sort calls by file and line
    def key_func(a: Dict) -> str:
        return a['file'] + a['line']
    calls.sort(key=key_func)
    print(f'[{func}] total: {total}, included: {len(calls)}')
    return calls

# Parse a single call's code and tokenize the format string

def parse_token_start(state: Dict, type: str) -> Dict:
    if PARSER_DEBUG:
        print('parse_token_start')
    state['token_start'] = state['pos']
    state['in_' + type] = True
    return state

def parse_token_end(state: Dict) -> Dict:
    if PARSER_DEBUG:
        print('parse_token_end')

    plus = 0
    if state['in_string'] and state['in_literal']:
        bad_line("Both string and literal tokens detected at the same time", state['code'])
    elif state['in_string']:
        _type = 'string'
        plus = 1 # the character ending a string literal belongs to it
    elif state['in_literal']:
        _type = 'literal'
    else:
        bad_line("End of an unknown token detected", state['code'])

    if state['token_start'] is None:
        bad_line("End of a {_type} without the beginning", state['code'])
    state['tokens'].append(state['code'][state['token_start']:(state['pos'] + plus)])
    state['token_start'] = None
    state['in_' + _type] = False
    return state

def parse_call_quote(state: Dict) -> Dict:
    if PARSER_DEBUG:
        print('parse_call_quote')
    if state['in_string']:
        if state['code'][state['pos'] - 1] == '\\': # escaped
            pass
        else:
            state = parse_token_end(state) #  string token ends here
    elif state['in_literal']:
        state = parse_token_end(state) # a literal token ends here
        state = parse_token_start(state, 'string') # a string token starts here...
    else:
        state = parse_token_start(state, 'string') # ... and here as well.
    return state

def parse_call_comma_or_rbracket(state: Dict) -> Dict:
    if PARSER_DEBUG:
        print('parse_call_comma_or_rbracket')
    if state['in_string']:
        pass
    elif state['in_literal']:
        state = parse_token_end(state) # a literal token ends here
        state['end'] = True # the format ends here...
    else:
        state['end'] = True # ... and here
    return state

def parse_call_AZaz09(state: Dict) -> Dict:
    if PARSER_DEBUG:
        print('parse_call_AZaz09')
    if state['in_string']:
        pass
    elif state['in_literal']:
        pass
    else:
        state = parse_token_start(state, 'literal')
    return state

def parse_call_space_or_minus(state: Dict) -> Dict:
    if PARSER_DEBUG:
        print('parse_call_space_or_minus')
    if state['in_string']:
        pass
    elif state['in_literal']:
        state = parse_token_end(state) # a literal token ends here
    return state

def parse_call_odd(state: Dict) -> Dict:
    if PARSER_DEBUG:
        print('parse_call_odd')
    if state['in_string']:
        pass
    else:
        ch = state['code'][state['pos']]
        bad_line('Unexpected "{ch}"', state['code'])
    return state

PARSER_CHAR_ACTION = {
    '"': parse_call_quote,
    ',': parse_call_comma_or_rbracket,
    ')': parse_call_comma_or_rbracket,
    ' ': parse_call_space_or_minus,
    '-': parse_call_space_or_minus,
    '(': parse_call_odd,
    '#': parse_call_odd,
    '%': parse_call_odd,
    ':': parse_call_odd,
    '+': parse_call_odd,
    '\'': parse_call_odd,
    '/': parse_call_odd,
    '.': parse_call_odd,
    '\\': parse_call_odd,
    '<': parse_call_odd,
    '>': parse_call_odd,
    '=': parse_call_odd,
    ';': parse_call_odd,
    '[': parse_call_odd,
    ']': parse_call_odd,
    '!': parse_call_odd,
    '|': parse_call_odd,
    'A-Za-z0-9_': parse_call_AZaz09,
}

def call_get_format_tokens(call):
    code = call['code']
    start = code.find('(')
    state = {
        'code': code,
        'pos': None,
        'end': False,
        'in_string': False,
        'in_literal': False,
        'token_start': None,
        'tokens': []
    }
    for i in range(start + 1, len(code)):
        state['pos'] = i
        ch = code[i]
        if ch in PARSER_CHAR_ACTION.keys():
            state = PARSER_CHAR_ACTION[ch](state)
        elif ch.isalpha() or ch.isdecimal() or ch == '_':
            state = PARSER_CHAR_ACTION['A-Za-z0-9_'](state)
        else:
            bad_line(f'Unsupported character \'{ch}\'', code)
        if state['end']:
            break
    if not state['end']:
        bad_line('Cannot find the end of the format string', code)
    return state['tokens']

# Generate a complete format string

LITERAL_TO_STRING = {
    'PRIx64': 'lx',
    'PRIu64': 'lu'
}

def token_stringify(token: str) -> str:
    if token[0] == '"' and token[-1] == '"':
        return token[1:-1] # strip quotes
    if token in LITERAL_TO_STRING.keys():
        return LITERAL_TO_STRING[token]
    else:
        print(f'Unknown token: "{token}"')
        exit(1)

def format_stringify(tokens: List) -> str:
    tokens_str = [token_stringify(token) for token in tokens]
    return ''.join(tokens_str)

# Identify required arguments

SPECIFIERS = [
    'd',
    'x',
    'u',
    's',
    'p',
    'o',
    'i',
]

FORMAT_SPECIFIER_ARGS = {
    '%s':   '_s',
    '%.8s': '_8s',
    '%x':   '_u',
    '%lx':  '_lu',
    '%#x':  '_u',
    '%d':   '_d',
    '%ld':  '_ld',
    '%u':   '_u',
    '%lu':  '_lu',
    '%zu':  '_zu',
    '%ju':  '_ju',
    '%p':   '_p',
    '%o':   '_u',
    '%i':   '_d',
    '%li':  '_d',
}

def arg_identify(format: str, pos: int):
    format_spec = None
    end_pos = None
    for i in range(pos + 1, len(format)):
        ch = format[i]
        if ch in SPECIFIERS:
            format_spec = format[pos:i + 1]
            end_pos = i + 1
            break
    if format_spec is None:
        visited = format[pos:]
        print(f'Unrecognized specifier: "{visited}"')
        exit(1)
    if format_spec not in FORMAT_SPECIFIER_ARGS.keys():
        print(f'Unrecognized format specifier: "{format_spec}"')
        exit(1)
    return FORMAT_SPECIFIER_ARGS[format_spec], end_pos

def args_parse(format: str) -> List:
    pos = 0
    args = []
    while True:
        pos = format.find('%', pos)
        if pos == -1:
            break
        arg, pos = arg_identify(format, pos)
        args.append(arg)
    return args

# Process raw source code: generate the complete format string and list of args

def calls_process(calls: List) -> List:
    for call in calls:
        call['format_tokens'] = call_get_format_tokens(call)
        call['format_string'] = format_stringify(call['format_tokens'])
        call['args'] = args_parse(call['format_string'])
    return calls

# Generate the call all source file

def init_source_file():
    with open(OUTPUT_C, 'w') as file:
        file.write(NOTICE)

def generate_call(file, func: str, call: Dict) -> str:
    if len(call['args']) > 0:
        args = ', ' + ', '.join(call['args'])
    else:
        args = ''
    file.write(f'\t// src/{call["file"]}:{call["line"]}\n')
    file.write(f'\t{func}("{call["format_string"]}"{args});\n')

def generate_func_with_errno(func: str, calls: List[Dict]) -> None:
    with open(OUTPUT_C, 'a') as file:
        file.write(C_FUNCTION_W_ERRNUM_PREFIX.format(func))
        for call in calls:
            generate_call(file, func, call)
            file.write('\tUT_ASSERTeq(errno, errnum);\n')
        file.write(C_FUNCTION_SUFFIX)

def generate_func(func: str, calls: List[Dict]) -> None:
    with open(OUTPUT_C, 'a') as file:
        file.write(C_FUNCTION_PREFIX.format(func))
        for call in calls:
            generate_call(file, func, call)
        file.write(C_FUNCTION_SUFFIX)

# Main

API = {
    'void': [
        'CORE_LOG_ERROR_LAST',
        'ERR_WO_ERRNO',
        'CORE_LOG_WARNING',
        'CORE_LOG_ERROR',
        'CORE_LOG_FATAL',
    ],
    'errno': [
        'CORE_LOG_ERROR_W_ERRNO_LAST',
        'ERR_W_ERRNO',
        'CORE_LOG_WARNING_W_ERRNO',
        'CORE_LOG_ERROR_W_ERRNO',
        'CORE_LOG_FATAL_W_ERRNO'
    ]
}

def main():
    global_total = 0
    init_source_file()

    for func in API['void']:
        calls = extract_all_calls(func)
        global_total += len(calls)
        calls = calls_process(calls)
        generate_func(func, calls)

    for func in API['errno']:
        calls = extract_all_calls(func)
        global_total += len(calls)
        calls = calls_process(calls)
        generate_func_with_errno(func, calls)

    print(f'Total: {global_total}')

if __name__ == '__main__':
    main()
