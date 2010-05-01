# -*- coding: utf-8 -*-
"""
    test_karnickel
    ~~~~~~~~~~~~~~

    Test for karnickel, AST macros for Python.

    :copyright: Copyright 2010 by Georg Brandl.
    :license: BSD, see LICENSE for details.
"""

import ast
import sys
from textwrap import dedent

from karnickel import *


def raises(exc, func, *args, **kwds):
    """Utility: Make sure the given exception is raised."""
    try:
        func(*args, **kwds)
    except exc:
        return True
    else:
        raise AssertionError('%s did not raise %s' % (func, exc))


@macro
def foo(x, y):
    x = 2*y

@macro
def bar():
    pass

test_macros = parse_macros('''
import os  # unrelated

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

def test_import_from():
    ns = expand_in(dedent('''
    from test_karnickel.__macros__ import foo
    foo(a, 21)
    '''))
    assert ns['a'] == 42

def test_expr_macro():
    # expr macros can be used in expressions or as expr statements
    assert expand_in('k = add(1, 2, 3)')['k'] == 6
    assert expand_in('class X: pass\no = X(); set_x(o)')['o'].x == 1
    # only calls are expanded
    assert expand_in('add = 1; add')['add'] == 1
    # invalid # of arguments
    assert raises(MacroCallError, expand_in, 'add(1)')

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
    # invalid # of arguments
    assert raises(MacroCallError, expand_in, 'assign(i)')

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
    # test that unrelated with statements are left alone
    assert raises(NameError, expand_in, 'with a: pass')

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

def test_import_macros():
    # test import_macros function
    macros = import_macros('test_karnickel', {'foo': 'fuu', 'bar': 'bar'}, {})
    assert 'fuu' in macros
    assert 'bar' in macros

    macros = import_macros('test_karnickel', {'*': '*'}, {})
    assert 'foo' in macros
    assert 'bar' in macros

    assert raises(MacroDefError, import_macros, 'some_module', {}, {})
    assert raises(MacroDefError, import_macros, 'test_karnickel', {'x': ''}, {})

def test_import_hook():
    importer = install_hook()
    import example.test
    assert example.test.usage_expr() == 22
    try:
        import example.fail
    except ImportError, err:
        assert '__body__' in str(err)
    else:
        assert False, 'ImportError not raised'
    # test import of builtin module, should still work normally
    import xxsubtype
    assert xxsubtype.spamdict
    # test import of C module
    import _testcapi
    assert _testcapi.error
    remove_hook()
    # test calling load_module without find_module
    assert raises(ImportError, importer.load_module, 'foo')
