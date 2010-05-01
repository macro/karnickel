# always import macros from ``module.__macros__``, after the
# import hook is installed
from example.macros.__macros__ import add, assign, custom_loop

def usage_expr():
    # usage of expression macros (nested calls possible)
    return add(1, 2) + add(3, 4) + add(add(3, 4), 5)

def usage_block():
    # usage of a block macro that does j = 1
    assign(j, 1)
    return j

def usage_3():
    # usage of a block macro with body
    with custom_loop(10):
        print 'loop continues...'

# this would be an error: the loop needs a body
#custom_loop(5)

# this would be an error too
#with add(1, 2):
#    pass
