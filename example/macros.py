from karnickel import macro

@macro
def add(i, j):
    i + j

@macro
def assign(n, v):
    n = v

@macro
def custom_loop(i):
    for __x in range(i):
        print __x
        if __x < i-1:
            __body__
