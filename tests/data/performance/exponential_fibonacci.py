def fib(n):
    if n <= 1:
       return n
    else:
       return(fib(n-1) + fib(n-2))

# testing the function
print(fib(10))  # Output: 55
