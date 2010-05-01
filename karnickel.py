# -*- coding: utf-8 -*-
"""
    karnickel
    ~~~~~~~~~

    AST macros for Python.

    :copyright: Copyright 2010 by Georg Brandl.
    :license: BSD, see LICENSE for details.
"""

import os
import ast
import imp
import new
import sys
from copy import deepcopy
from itertools import izip


def macro(func):
    """Decorator to mark macros."""
    def new_func(*args, **kwds):
        raise RuntimeError('%s.%s() is a macro; you should not call it '
                           ' directly.' % (func.__module__, func.__name__))
    return new_func


class MacroDefError(Exception):
    """Raised when an invalid macro definition is encountered."""


def parse_macros(code):
    """Find and parse all macros in *code*.  Return a dictionary mapping macro
    names to MacroDefs.
    """
    code = ast.parse(code)
    macros = {}
    for item in code.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        if not (len(item.decorator_list) == 1 and
                isinstance(item.decorator_list[0], ast.Name) and
                item.decorator_list[0].id == 'macro'):
            continue
        name = item.name
        args = [arg.id for arg in item.args.args]
        if item.args.vararg or item.args.kwarg or item.args.defaults:
            raise MacroDefError('macro %s has an unsupported signature' % name)
        if len(item.body) == 1 and isinstance(item.body[0], ast.Expr):
            macro = ExprMacroDef(args, item.body[0].value)
        else:
            macro = BlockMacroDef(args, item.body)
        macros[name] = macro
    return macros


def import_macros(module, names, dict):
    """Import macros given in *names* from *module*, from a module with the
    given globals *dict*.
    """
    try:
        mod = __import__(module, dict, None, ['*'])
    except Exception, err:
        raise MacroDefError('macro module %s not found: %s' % (module, err))
    filename = mod.__file__
    if filename.lower().endswith(('c', 'o')):
        filename = filename[:-1]
    with open(filename, 'U') as f:
        code = f.read()
    all_macros = parse_macros(code)
    macros = {}
    for name, asname in names.iteritems():
        if name == '*':
            macros.update(all_macros)
            break
        try:
            macros[asname] = all_macros[name]
        except KeyError:
            raise MacroDefError('macro %s not found in module %s' %
                                (name, module))
    return macros


class MacroCallError(Exception):
    """Raised when an invalid macro call is encountered."""

    def __init__(self, node, message):
        Exception.__init__(self, '%s: %s' % (node.lineno, message))

    def add_filename(self, filename):
        self.args = [filename + ':' + self.args[0]]


class ContextChanger(ast.NodeVisitor):
    """
    AST visitor that updates the "context" on nodes that can occur on the LHS or
    RHS in an assignment.  This is needed because on a macro call, arguments
    always have Load context, while in the expansion, they can also have Store
    or other contexts.
    """

    def __init__(self, context):
        self.context = context

    def visit_Name(self, node):
        node.ctx = self.context
        self.generic_visit(node)  # visit children

    visit_Attribute = visit_Subscript = visit_List = visit_Tuple = visit_Name


class CallTransformer(ast.NodeTransformer):
    """
    AST visitor that expands uses of macro arguments and __body__ inside a macro
    definition.
    """

    def __init__(self, args, body=None):
        self.args = args
        self.body = body

    def visit_Name(self, node):
        if node.id in self.args:
            if not isinstance(node.ctx, ast.Load):
                new_node = deepcopy(self.args[node.id])
                ContextChanger(node.ctx).visit(new_node)
            else:
                new_node = self.args[node.id]
            return new_node
        return node

    def visit_Expr(self, node):
        node = self.generic_visit(node)
        if self.body and isinstance(node.value, ast.Name) and \
           node.value.id == '__body__':
            new_node = ast.fix_missing_locations(ast.If(ast.Num(1),
                                                        self.body, []))
            return new_node


class BodyVisitor(ast.NodeVisitor):
    """
    AST visitor that checks for use of __body__, to determine if a block macro
    has a body.
    """

    def __init__(self):
        self.found_body = False

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == '__body__':
            self.found_body = True


class ExprMacroDef(object):
    """
    Definition of an expression macro.
    """

    def __init__(self, args, expr):
        self.args = args
        self.expr = expr
        self.has_body = False

    def expand(self, node, call_args, body=None):
        assert not body
        if len(call_args) != len(self.args):
            raise MacroCallError(node, 'invalid number of arguments')
        expr = deepcopy(self.expr)
        argdict = dict(izip(self.args, call_args))
        return CallTransformer(argdict).visit(expr)


class BlockMacroDef(object):
    """
    Definition of a block macro, with or without body.
    """

    def __init__(self, args, stmts):
        self.args = args
        self.stmts = stmts
        visitor = BodyVisitor()
        visitor.visit(ast.Module(stmts))
        self.has_body = visitor.found_body

    def expand(self, node, call_args, body=None):
        if len(call_args) != len(self.args):
            raise MacroCallError(node, 'invalid number of arguments')
        stmts = deepcopy(self.stmts)
        argdict = dict(izip(self.args, call_args))
        new_node = ast.fix_missing_locations(ast.If(ast.Num(1), stmts, []))
        return CallTransformer(argdict, body).visit(new_node)


class Expander(ast.NodeTransformer):
    """
    AST visitor that expands macros.
    """

    def __init__(self, module, macro_definitions=None):
        self.module = module
        self.defs = macro_definitions or {}

    def visit_ImportFrom(self, node):
        if node.module and node.module.endswith('.__macros__'):
            modname = node.module[:-11]
            names = dict((alias.name, alias.asname or alias.name)
                         for alias in node.names)
            self.defs.update(import_macros(
                modname, names, self.module and self.module.__dict__))
            return None
        return node

    def visit_With(self, node):
        expanded_body = map(self.visit, node.body)
        expr = node.context_expr
        if isinstance(expr, ast.Call) and \
           isinstance(expr.func, ast.Name) and expr.func.id in self.defs:
            #if node.optional_vars:
            #    raise MacroCallError(node, '"with" macro call with "as" clause')
            if expr.keywords or expr.starargs or expr.kwargs:
                raise MacroCallError(node, 'macro call with kwargs or star syntax')
            macro_def = self.defs[expr.func.id]
            if not isinstance(macro_def, BlockMacroDef):
                raise MacroCallError(node, 'macro is not a block macro')
            if not macro_def.has_body:
                raise MacroCallError(node, 'macro has no __body__ substitution')
            return macro_def.expand(node, expr.args, expanded_body)
        return node

    def _handle_call(self, node, macrotype):
        if node.keywords or node.starargs or node.kwargs:
            raise MacroCallError(node, 'macro call with kwargs or star syntax')
        macro_def = self.defs[node.func.id]
        if not isinstance(macro_def, macrotype):
            raise MacroCallError(node, 'macro is not a %s' % macrotype)
        if macro_def.has_body:
            raise MacroCallError(node, 'macro has a __body__ substitution')
        expanded_args = map(self.visit, node.args)
        return macro_def.expand(node, expanded_args)

    def visit_Expr(self, node):
        value = node.value
        if isinstance(value, ast.Call) and \
           isinstance(value.func, ast.Name) and value.func.id in self.defs:
            ret = self._handle_call(value, (ExprMacroDef, BlockMacroDef))
            if isinstance(ret, ast.expr):
                ret = ast.fix_missing_locations(ast.Expr(ret))
            return ret
        return node

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in self.defs:
            return self._handle_call(node, ExprMacroDef)
        return node


class MacroImporter(object):
    """
    Import hook for use on `sys.meta_path`, to expand macros on import.  Quite a
    pain without having importlib.
    """

    def __init__(self):
        self._cache = {}

    def find_module(self, name, path=None):
        try:
            lastname = name.split('.')[-1]
            self._cache[name] = imp.find_module(lastname, path), path
        except ImportError:
            return None
        return self

    def load_module(self, name):
        try:
            (fd, fn, info), path = self._cache[name]
        except KeyError:
            # can that happen?
            raise ImportError(name)
        if info[2] == imp.PY_SOURCE:
            newpath = None
            filename = fn
            with fd:
                code = fd.read()
        elif info[2] == imp.PY_COMPILED:
            newpath = None
            filename = fn[:-1]
            with open(filename, 'U') as f:
                code = f.read()
        elif info[2] == imp.PKG_DIRECTORY:
            filename = os.path.join(fn, '__init__.py')
            newpath = [fn]
            with open(filename, 'U') as f:
                code = f.read()
        else:
            return imp.load_module(name, fd, fn, info)
        try:
            module = new.module(name)
            module.__file__ = filename
            if newpath:
                module.__path__ = newpath
            tree = ast.parse(code)
            try:
                transformed = Expander(module).visit(tree)
            except MacroCallError, err:
                err.add_filename(filename)
                raise
            code = compile(transformed, filename, 'exec')
            sys.modules[name] = module
            exec code in module.__dict__
            return module
        except Exception, err:
            raise ImportError('cannot import %s: %s' % (name, err))


def install_hook():
    """Install the import hook that allows to import modules using macros."""
    importer = MacroImporter()
    sys.meta_path.insert(0, importer)
    return importer


def remove_hook():
    """Remove any MacroImporter from `sys.meta_path`."""
    sys.meta_path[:] = [importer for importer in sys.meta_path if
                        not isinstance(importer, MacroImporter)]
