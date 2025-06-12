import pyafl

# 如果你在 libafl.pyx 中定义了 hello_world()
pyafl.hello_world()
pyafl.print("1111111111\n")


path = "conf.json"

with open(path,'r') as f:
    data = f.read()

# print(data)

# a = pyafl.read_json(data)
# a = pyafl.init(data,1)

# print(a)