from setuptools import setup, Extension
from Cython.Build import cythonize
import os

# 获取 PREFIX 或使用默认值
PREFIX = os.getenv("PREFIX", "/usr/local")
BIN_PATH = os.getenv("BIN_PATH", f"{PREFIX}/bin")
HELPER_PATH = os.getenv("HELPER_PATH", f"{PREFIX}/lib/afl")
DOC_PATH = os.getenv("DOC_PATH", f"{PREFIX}/share/doc/afl")

# 定义宏（注意：字符串要用双引号包裹）
define_macros = [
    ("AFL_PATH", f'"{HELPER_PATH}"'),
    ("DOC_PATH", f'"{DOC_PATH}"'),
    ("BIN_PATH", f'"{BIN_PATH}"'),
    ("_FORTIFY_SOURCE", "2"),
]

# 编译参数
extra_compile_args = [
    "-O3",
    "-funroll-loops",
    "-fPIC",
    "-Wall",
    "-g",
    "-Wno-pointer-sign",
    "-Wno-unused-result",
]

# 链接参数
extra_link_args = []
if os.uname().sysname in ["Linux", "GNU"]:
    extra_link_args.extend(["-ldl", "-lgvc", "-lcgraph", "-lm"])

# 构建模块
extensions = [
    Extension(
        "pyafl",
        sources=["pyafl.pyx"],  # 只包含 pyx，C 文件通过 #include 引入
        libraries=["cjson", "m"],  # 使用系统库 -lcjson -lm
        include_dirs=[],
        define_macros=define_macros,
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
]

setup(
    name="pyafl",
    ext_modules=cythonize(extensions),
)