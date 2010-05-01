from example.macros.__macros__ import add, assign, custom_loop

print add(1, 2) + add(3, 4)

assign(j, 1)
print j

with custom_loop(10):
    print 'loop continues...'

# would be an error
#custom_loop(5)

# would be an error too
#with add(1, 2):
#    pass
