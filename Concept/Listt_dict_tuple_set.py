doubles = [x*2 for x in range(1,10) if x > 5]
# print(doubles)

# Valid dictionary - immutable keys, any values
user_data = {
    "name": "Alice",           # string key, string value
    42: [1, 2, 3],             # integer key, list value
    (10, 20): {"nested": True} # tuple key, dict value
}
print(type(user_data), "valid dict")

# Invalid - will raise TypeError
try:
    invalid_dict = {[1, 2]: "value"}  # lists are not hashable
except TypeError as e:
    print(f"Error: {e}")