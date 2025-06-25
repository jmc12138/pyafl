my_list = [10, 20, 30]
index = 3
elements_to_insert = [1]

for val in reversed(elements_to_insert):
    my_list.insert(index, val)

print(my_list)  # 输出: [10, 99, 88, 77, 20, 30]