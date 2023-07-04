class Cache:
    def __init__(self):
        # Initialize a cache with some predefined values
        self.cache = {str(i): i for i in range(10000)}

    def lookup_value(self, key):
        # Constant time operation O(1)
        if key in self.cache:
            return self.cache[key]
        else:
            return None

# Example usage:
my_cache = Cache()
print(my_cache.lookup_value('500'))  # Outputs: 500
print(my_cache.lookup_value('10000'))  # Outputs: None
