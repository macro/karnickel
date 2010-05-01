# -*- coding: utf-8 -*-
"""
    test_karnickel
    ~~~~~~~~~~~~~~

    Test for karnickel, AST macros for Python.

    :copyright: Copyright 2010 by Georg Brandl.
    :license: BSD, see LICENSE for details.
"""

import ast
from textwrap import dedent

from karnickel import *


def raises(exc, func, *args, **kwds):
    try:
        func(*args, **kwds)
    except exc:
        return True
    else:
        raise AssertionError('%s did not raise %s' % (func, exc))

test_macros = parse_macros('''

import os

def not_a_macro():
    pass

@macro
def add(i, j, k):
    i + j + k

@macro
def set_x(o):
    setattr(o, 'x', 1)

@macro
def assign(name, value):
    name = value

@macro
def do_while(cond):
    while True:
        __body__
        if not cond: break

''')

def expand_in(code):
    ex = Expander(None, test_macros)
    tree = ast.parse(code)
    new_tree = ex.visit(tree)
    code = compile(new_tree, '<test>', 'exec')
    ns = {}
    exec code in ns
    return ns

def test_macro_decorator():
    @macro
    def test():
        pass
    # test that a function marked as "macro" can't be called as an
    # ordinary function
    assert raises(RuntimeError, test)

def test_parse():
    # only functions decorated with @macro are macros
    assert 'not_a_macro' not in test_macros
    # test categorization
    assert isinstance(test_macros['add'], ExprMacroDef)
    assert isinstance(test_macros['assign'], BlockMacroDef)
    assert isinstance(test_macros['do_while'], BlockMacroDef)
    # test __body__ presence
    assert not test_macros['assign'].has_body
    assert test_macros['do_while'].has_body
    # invalid macro definitions
    assert raises(MacroDefError, parse_macros, dedent('''
    @macro
    def foo(x, y=1): pass
    '''))

def test_expr_macro():
    # expr macros can be used in expressions or as expr statements
    assert expand_in('k = add(1, 2, 3)')['k'] == 6
    assert expand_in('class X: pass\no = X(); set_x(o)')['o'].x == 1

def test_block_macro():
    # in particular, this tests context reassignment
    ns = expand_in('assign(j, 1); assign(k, j+1)')
    assert ns['j'] == 1
    assert ns['k'] == 2
    ns = expand_in('assign([j, k], [1, 2])')
    assert ns['j'] == 1
    assert ns['k'] == 2
    # block macros cannot be used as expressions
    assert raises(MacroCallError, expand_in, 'k = assign(j, 1)')
    # block macros without __body__ cannot be used in with blocks
    assert raises(MacroCallError, expand_in, 'with assign(j, 1): pass')

def test_body_macro():
    ns = expand_in(dedent('''
    i = 0
    with do_while(i != 0):
        j = 1
    '''))
    assert ns['j'] == 1
    # block macros with __body__ cannot be used in expressions or
    # as expr statements
    assert raises(MacroCallError, expand_in, 'k = do_while(1)')
    assert raises(MacroCallError, expand_in, 'do_while(1)')

def test_recursive_expansion():
    # test that arguments are expanded before being inserted
    ns = expand_in(dedent('''
    k = add(add(1, 2, 3), 4, 10)
    '''))
    assert ns['k'] == 20
    # test that the macro body is expanded before being inserted
    ns = expand_in(dedent('''
    with do_while(False):
        k = add(5, 5, 5)
    '''))
    assert ns['k'] == 15
