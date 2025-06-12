# distutils: language = c

#include "config.h"
#include "debug.h"
#include "types.h"

# 引入 AFL 的 C 逻辑
#include "afl-fuzz.c"

# 声明你想调用的 C 函数（不暴露给 Python）
cdef extern from "afl-fuzz.c":
    void __hello_world()


def hello_world():
    __hello_world()


# 声明外部 C 函数
cdef extern void __print(char* str)

# 创建一个 Python 封装函数
def print(str):
    # 转换 Python 字符串为 C 字符串
    cdef bytes temp = str.encode('utf-8')
    cdef char* c_str = temp
    # 调用 C 函数
    __print(c_str)


