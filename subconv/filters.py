"""Validate the shared Python/regexp2 filter syntax and normalize named groups."""

import re
from functools import lru_cache


_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_NAMED_GROUP = re.compile(r"\(\?(?:P<|<)(" + _NAME + r")>")
_NAMED_REFERENCE = re.compile(r"\(\?P=(" + _NAME + r")\)")
_DOTNET_REFERENCE = re.compile(r"\\k<(" + _NAME + r")>")
_FLAGS = re.compile(r"\(\?([aiLmsux]*)(?:-([imsx]+))?([:)])")
_QUANTIFIER = re.compile(r"\{([0-9]*)(?:,([0-9]*))?\}")


@lru_cache(maxsize=128)
def compile_group_filter(source: str) -> tuple[tuple[re.Pattern, ...], str]:
    patterns, output = [], []
    for part in source.split('`'):
        local, remote = _normalize(part)
        try:
            patterns.append(re.compile(local, re.I))
        except (re.error, OverflowError, RecursionError) as exc:
            raise ValueError(f"Unsupported group filter: {exc}") from exc
        output.append('(?i)' + remote)
    return tuple(patterns), '`'.join(output)


def ambiguous_unicode_names(names) -> set[str]:
    # Unicode tables and case folding differ between Python and regexp2.
    return {name for name in names if not name.isascii() or any('\x1c' <= char <= '\x1f' for char in name)}


def filter_names(patterns: tuple[re.Pattern, ...], names: list[str]) -> list[str]:
    # mihomo applies filters in order, retaining the first occurrence of a node.
    result, seen = [], set()
    for pattern in patterns:
        for name in names:
            if name not in seen and pattern.search(name):
                seen.add(name)
                result.append(name)
    return result


def _normalize(source: str) -> tuple[str, str]:
    local, remote = [], []
    scopes = []
    verbose = False
    class_start = None
    index = 0
    while index < len(source):
        char = source[index]
        token = char
        local_token = remote_token = token
        if char == '\\' and index + 1 < len(source):
            token = source[index:index + 2]
            escape = source[index + 1]
            if escape in '123456789NU':
                raise ValueError('Group filters do not support numeric references or \\N/\\U escapes')
            local_token = remote_token = token
            if escape == '_' or not escape.isascii():
                # Python allows escaping literal Unicode/underscore, whereas
                # regexp2 can treat those escapes as invalid word characters.
                local_token = remote_token = escape
            if class_start is None:
                if escape == 'k':
                    reference = _DOTNET_REFERENCE.match(source, index)
                    if reference is None:
                        raise ValueError('Invalid named group reference')
                    token = reference[0]
                    local_token, remote_token = f'(?P={reference[1]})', token
                elif escape == 'z':
                    local_token = r'\Z'
                elif escape == 'Z':
                    # SubConv's Python \Z is strict; regexp2 spells it \z.
                    remote_token = r'\z'
        elif class_start is not None:
            if char == '[':
                raise ValueError('Nested/subtracted character classes are not supported')
            if char == '^' and index == class_start and source[index - 1] == '[':
                class_start += 1
            elif char == ']' and index != class_start:
                class_start = None
        elif verbose and char == '#':
            end = source.find('\n', index)
            token = source[index:end if end >= 0 else len(source)]
            local_token = remote_token = token
        elif source.startswith('(?#', index):
            end = index + 3
            while end < len(source) and source[end] != ')':
                end += 2 if source[end] == '\\' else 1
            if end >= len(source):
                raise ValueError('Unclosed group filter comment')
            token = source[index:end + 1]
            # Comment escape rules differ between engines. Comments have no
            # matching effect, so omit the complete Python comment in output.
            local_token = remote_token = ''
        elif char == '[':
            class_start = index + 1
        elif char == '(':
            named = _NAMED_GROUP.match(source, index)
            reference = _NAMED_REFERENCE.match(source, index)
            flags = _FLAGS.match(source, index)
            if source.startswith('(?(', index):
                raise ValueError('Conditional groups are not supported')
            if named:
                token = named[0]
                local_token = f'(?P<{named[1]}>'
                remote_token = f'(?<{named[1]}>'
                scopes.append(verbose)
            elif reference:
                token = local_token = reference[0]
                remote_token = f'\\k<{reference[1]}>'
            elif source.startswith(('(?P<', '(?P='), index):
                raise ValueError('Group filter names must be ASCII identifiers')
            elif flags:
                if any(flag in flags[1] for flag in 'aLu'):
                    raise ValueError('Group filter flags are limited to i/m/s/x')
                token = local_token = remote_token = flags[0]
                if flags[3] == ':':
                    scopes.append(verbose)
                verbose = (verbose or 'x' in flags[1]) and 'x' not in (flags[2] or '')
            else:
                scopes.append(verbose)
        elif char == ')' and scopes:
            verbose = scopes.pop()
        elif char in '*+?' and source[index + 1:index + 2] == '+':
            raise ValueError('Possessive quantifiers are not supported')
        elif char == '{' and (quantifier := _QUANTIFIER.match(source, index)):
            token = quantifier[0]
            for count in quantifier.groups():
                digits = (count or '').lstrip('0')
                if len(digits) > 10 or (len(digits) == 10 and digits > '2147483647'):
                    raise ValueError('Group filter quantifier exceeds the regexp2 limit')
            if source[index + len(token):index + len(token) + 1] == '+':
                raise ValueError('Possessive quantifiers are not supported')
            if not quantifier[1] and quantifier[2] is not None:
                raise ValueError('Group filters require an explicit quantifier minimum')
            else:
                local_token = remote_token = token
        local.append(local_token)
        remote.append(remote_token)
        index += len(token)
    return ''.join(local), ''.join(remote)
