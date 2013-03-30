.. -*- restructuredtext -*-

============================================
README for Karnickel - AST Macros for Python
============================================

"it's no ordinary rabbit..."


What is it?
===========

Karnickel is a small library that allows you to use macros (similar to those
found in Lisp) in Python code.  In a nutshell, macros allow you to insert code
(the macro *definition*) at a different point in the code (the macro *call*).
It is different from calling functions in that the code is inserted *before* it
is even compiled.

("Karnickel" is German for "rabbit", and there's a vicious killer
rabbit in "Monty Python and the Holy Grail" that is best left alone...)


Using
=====

Use Python 2.6+.  You can put macros in any module.  Macro definitions are
Python functions, like this::

   from karnickel import macro

   @macro
   def macroname(arg1, arg2):
        ... macro contents ...

Optional arguments are not supported.

If the contents are a single expression (no ``return``), the macro is an
*expression macro*.  Otherwise, it is a *block macro*.  If it contains a
statement consisting of only ``__body__``, it is a block macro *with body*.

For using the macros, you must install the import hook::

   import karnickel
   karnickel.install_hook()

*Then*, you can import modules that use macros like this::

   from module.__macros__ import macro1, macro2

That is, append ``.__macros__`` to the name of the module that contains the
macros.  Only ``from``-imports are supported.

Usage depends on the macro type:

* Expression macros can be used everywhere as expressions.  Arguments are put
  into the places of macro arguments.

* Block macros without body can only be used as an expression statement --
  i.e.::

     macroname(arg1, arg2)

* Block macros with body must be used with a ``with`` statement::

     with macroname(arg1, arg2):
         body

  Arguments are put into the places of macro arguments, and the body is put into
  the place of ``__body__`` in the macro definition.

Proper docs may follow as soon as I can find a decent documentation tool.


Why?
====

Why not?  Seriously, this is a demonstration of what you can do with the Python
AST, especially the standard ``ast`` module, and import hooks.  Besides, it's
been fun.


Installing
==========

Use ``setup.py``::

   sudo python setup.py install


Author
======

Georg Brandl <georg@python.org>
