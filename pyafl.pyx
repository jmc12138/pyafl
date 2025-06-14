# distutils: language = c

#include "config.h"
#include "debug.h"
#include "types.h"

from cpython.bytes cimport PyBytes_AsString, PyBytes_GET_SIZE

# 引入 AFL 的 C 逻辑
#include "afl-python.c"

# 声明你想调用的 C 函数（不暴露给 Python）
cdef extern from "afl-python.c":
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



cdef extern int __parse_args(const char *json_str)

def parse_args(json_str):
    cdef bytes temp = json_str.encode('utf-8')
    cdef char* c_str = temp

    return __parse_args(c_str)



cdef extern void __set_up()

def set_up():

    return __set_up()



cdef extern void __clear()

def clear():

    return __clear()



cdef extern void __debug()

def debug():

    return __debug()


cdef extern char* __get_response_buf()
cdef extern int __get_response_buf_len()

def get_response_buff():
    """
    获取全局响应缓冲区的Python接口
    
    返回:
        bytes: 从C全局缓冲区获取的数据
    """
    cdef char* buf = __get_response_buf()
    len_buf = __get_response_buf_len()
    if buf == NULL :
        return b""
    return buf[:len_buf]  


cdef extern int __pre_run_target(unsigned int timeout)
cdef extern void __run_target()
cdef extern int __post_run_target(unsigned int timeout)

cdef extern void __get_test_case(const char *buf, size_t buf_len) 
cdef extern unsigned int __get_exec_tmout()

cdef extern unsigned int __trace_bytes_count()
cdef extern unsigned int __var_bytes_count()
cdef extern unsigned int __trace_hash32()

def get_exec_tmout():
    return __get_exec_tmout()


def trace_hash32():
    return __trace_hash32()


def trace_bytes_count():
    return __trace_bytes_count()


def var_bytes_count():
    return __var_bytes_count()

def pre_run_target(timeout):
    
    return __pre_run_target(timeout)




def run_target(bytes buf):
    cdef char* c_str = PyBytes_AsString(buf)
    cdef int length = PyBytes_GET_SIZE(buf)

    __get_test_case(c_str,length)

    return __run_target()



def post_run_target(timeout):

    return __post_run_target(timeout)
