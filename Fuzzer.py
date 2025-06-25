import pyafl
import json
import struct
from typing import List, Tuple
import os
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.box import ROUNDED
from rich.text import Text
from rich.panel import Panel
import humanize
from datetime import datetime
from utils import PcapGenerator
from enum import Enum, auto
import time
import utils
import signal
from line_profiler import LineProfiler,profile
import random
import copy,os
from typing import List


class FaultCode(Enum):
    """Execution status fault codes"""
    NONE = 0      # 00 - No error
    TMOUT = 1     # 01 - Timeout
    CRASH = 2     # 02 - Crash
    ERROR = 3     # 03 - Error
    NOINST = 4    # 04 - No instrumentation detected
    NOBITS = 5    # 05 - No new bits found


class Stats:
    def __init__(self):
        self.total_tmouts = 0
        self.unique_tmouts = 0
        self.unique_hangs = 0
        self.last_hang_time = 0

        self.total_crashes = 0
        self.unique_crashs = 0

        self.unique_favors = 0
        self.queue_len = 0

        self.favor_paths = 0
        self.total_exec = 0
        self.stage_name = 0

        self.queued_with_cov = 0

        self.queue_cycle = 0

class TestCase:
    def __init__(self,file_path , messages):
        self.file_path = file_path
        self.messages  = messages
        self.cksum =  0       #覆盖率的hash32
        self.bitmap_size = 0
        self.exec_us = 0      #执行时间
        self.file_len =  os.path.getsize(file_path) if file_path  else None 
        self.messages_len = len(messages)
        self.var_behavior = 0 # 多次运行覆盖率是否变化
        
        self.cal_failed = 0
        self.trim_done = 0
        self.was_fuzzed = 0
        self.has_new_cov = 0
        self.favored = 0
        self.depth = 0

        self.trace_mini = 0
        self.trace_mini_hash = 0 # for favor path selection

        self.handicap = 0



    def show_status(self):
        """打印测试用例的所有状态信息"""
        print("\n=== TestCase Status ===")
        print(f"File Path: {self.file_path}")
        print(f"File Length: {self.file_len} bytes")
        print(f"Messages Count: {self.messages_len}")
        print(f"Coverage Hash (cksum): {self.cksum}")
        print(f"Bitmap Size: {self.bitmap_size}")
        print(f"Execution Time: {self.exec_us} μs")
        print(f"Variable Behavior: {'Yes' if self.var_behavior else 'No'}")
        # print(f"Trace Mini Length: {len(self.trace_mini)} bytes")
        # print(f"Favored Status: {'Yes' if self.favored else 'No'}")
        # print(f"Redundant Status: {'Yes' if self.fs_redundant else 'No'}")
        print("=======================")


class Mutator:
    def __init__(self, extras = None):
        self.region_level_mutation = False


        self._rng = random.Random(12138)
        
        
        self.extras = extras or []      # 用户指定的 extras
        self.a_extras = []  # 自动检测的 extras
        
        self.INTERESTING_8 = [-128, -1, 0, 1, 16, 32, 64, 100, 127]
        self.INTERESTING_16 = [-32768, -129, 128, 255, 256, 512, 1000, 1024, 4096, 32767]
        self.INTERESTING_32 = [
            -2147483648, -100663046, -32769, 32768, 
            65535, 65536, 100663045, 2147483647
        ]
        self.ARITH_MAX = 35
    
    def mutate(self, messages: List[bytearray], msg_idx: int) -> None:
        """执行变异操作"""
        mutation_funcs = {
            0: self.flip_single_bit,
            1: self.interesting_8,
            2: self.interesting_16,
            3: self.interesting_32,
            4: self.subtract_from_byte,
            5: self.add_from_byte,
            6: self.subtract_from_word,
            7: self.add_from_word,
            8: self.subtract_from_dword,
            9: self.add_from_dword,
            10: self.random_xor_byte,
            11: self.delete_bytes,
            12: self.delete_bytes,
            13: self.clone_or_insert_block,
            14: self.overwrite_bytes,
            15: self.overwrite_with_extra,
            16: self.insert_with_extra,
            17: self.overwrite_with_region,
            18: self.insert_with_region,
            19: self.insert_with_region2,
            20: self.duplicate_region
        }
        msg = messages[msg_idx]
        # 根据 AFL 的概率分布选择变异方法
        choice = random.randint(0, 15 + 2 + (4 if self.region_level_mutation else 0))
        # choice = 11
        # print(msg)
        if choice in mutation_funcs:
            if choice <= 16:
                mutation_funcs[choice](msg)
            else:
                mutation_funcs[choice](messages, msg_idx)
        else:
            # 默认变异方法
            self.flip_single_bit(msg)
    


    @staticmethod
    def _choose_position(data: bytearray, width: int) -> int:
        """选择有效的变异位置"""
        if len(data) < width:
            raise ValueError(f"数据长度不足 {width} 字节")
        return random.randint(0, len(data) - width)



    def flip_single_bit(self, msg: bytearray) -> None:
        """翻转单个比特位"""

        bit_pos = random.randint(0, len(msg) * 8 - 1)
        byte_pos = bit_pos // 8
        bit_in_byte = bit_pos % 8
        
        # 翻转指定的比特位
        msg[byte_pos] ^= (1 << (7 - bit_in_byte))




    def interesting_8(self, msg: bytearray) -> None:
        """ 用特殊值替换随机字节 """
        if len(msg) < 1:
            return
        pos = self._rng.randint(0, len(msg) - 1)
        msg[pos] = self._rng.choice(self.INTERESTING_8) & 0xFF  # 确保8位范围

    def interesting_16(self, data: bytearray) -> None:
        if len(data) < 2:
            return
        """16位特殊值变异（自动处理字节序）"""
        pos = self._rng.randint(0, len(data) - 2)
        value = self._rng.choice(self.INTERESTING_16)
        # 随机选择大端或小端
        endian = 'big' if self._rng.choice([True, False]) else 'little'
        data[pos:pos+2] = value.to_bytes(2, endian, signed=True)


    def interesting_32(self, data: bytearray) -> None:
        """32位特殊值变异（自动处理字节序）"""

        if len(data) < 4:
            return
        pos = self._rng.randint(0, len(data) - 4)
        value = self._rng.choice(self.INTERESTING_32)
        
        # 随机选择字节序
        endian = 'big' if self._rng.choice([True, False]) else 'little'
        data[pos:pos+4] = value.to_bytes(4, endian, signed=True)


    def subtract_from_byte(self, data: bytearray) -> None:
        """随机从字节中减去一个值（1到ARITH_MAX+1的范围）"""
        if not data:
            return
            
        pos = self._rng.randint(0, len(data) - 1)
        value = 1 + self._rng.randint(0, self.ARITH_MAX - 1)
        data[pos] = (data[pos] - value) % 256  # 确保结果在0-255范围内
        
    
    def add_from_byte(self, data: bytearray) -> None:
        """随机从字节中add去一个值（1到ARITH_MAX+1的范围）"""
        if not data:
            return
            
        pos = self._rng.randint(0, len(data) - 1)
        value = 1 + self._rng.randint(0, self.ARITH_MAX - 1)
        data[pos] = (data[pos] + value) % 256  # 确保结果在0-255范围内
        

    def subtract_from_word(self, data: bytearray) -> None:
        """
        随机从16位字中减去一个值（1到ARITH_MAX+1的范围）
        自动处理大端/小端字节序
        """
        if len(data) < 2:
            return

        # 随机选择位置（确保有2字节空间）
        pos = self._rng.randint(0, len(data) - 2)
        delta = 1 + self._rng.randint(0, self.ARITH_MAX - 1)

        endian = 'big' if self._rng.choice([True, False]) else 'little'
        # 交换字节序后操作
        value = int.from_bytes(data[pos:pos+2], endian, signed=False)
        value = (value - delta) & 0xFFFF
        data[pos:pos+2] = value.to_bytes(2, endian)


    def add_from_word(self, data: bytearray) -> None:
        """
        随机从16位字中减去一个值（1到ARITH_MAX+1的范围）
        自动处理大端/小端字节序
        """
        if len(data) < 2:
            return

        # 随机选择位置（确保有2字节空间）
        pos = self._rng.randint(0, len(data) - 2)
        delta = 1 + self._rng.randint(0, self.ARITH_MAX - 1)

        endian = 'big' if self._rng.choice([True, False]) else 'little'
        # 交换字节序后操作
        value = int.from_bytes(data[pos:pos+2], endian, signed=False)
        value = (value + delta) & 0xFFFF
        data[pos:pos+2] = value.to_bytes(2, endian)
            
    def subtract_from_dword(self, data: bytearray) -> None:
        """32位减法变异（简化版）"""
        if len(data) < 4:
            return

        pos = self._rng.randint(0, len(data) - 4)
        delta = 1 + self._rng.randint(0, self.ARITH_MAX - 1)
        endian = 'little' if self._rng.choice([True, False]) else 'big'

        value = int.from_bytes(data[pos:pos+4], endian, signed=False)
        value = (value - delta) & 0xFFFFFFFF  # 处理32位溢出
        data[pos:pos+4] = value.to_bytes(4, endian)


    def add_from_dword(self, data: bytearray) -> None:
        """32位减法变异（简化版）"""
        if len(data) < 4:
            return

        pos = self._rng.randint(0, len(data) - 4)
        delta = 1 + self._rng.randint(0, self.ARITH_MAX - 1)
        endian = 'little' if self._rng.choice([True, False]) else 'big'

        value = int.from_bytes(data[pos:pos+4], endian, signed=False)
        value = (value + delta) & 0xFFFFFFFF  # 处理32位溢出
        data[pos:pos+4] = value.to_bytes(4, endian)

    def random_xor_byte(self, data: bytearray) -> None:
        """
        随机选择一个字节与1-255之间的值进行异或
        （确保不会无操作，因为异或0是无变化的）
        """
        if not data:  # 空数据检查
            return
        
        pos = self._rng.randint(0, len(data) - 1)
        xor_value = 1 + self._rng.randint(0, 254)  # 1-255范围
        data[pos] ^= xor_value

    def delete_bytes(self, data: bytearray) -> None:
        """
        随机删除一段字节（比插入操作更频繁，以控制文件大小）
        遵循AFL的删除概率分布（倾向于中等长度删除）
        """
        if len(data) < 2:  # 至少需要2字节才能删除
            return

        # 计算要删除的长度（AFL的choose_block_len逻辑）
        max_len = min(len(data) - 1, 64)  # AFL默认最大删除64字节
        del_len = self._choose_block_len(max_len)
        
        # 随机选择删除起始位置
        del_from = self._rng.randint(0, len(data) - del_len)
        
        # 执行删除（用切片操作替代memmove）
        data[del_from:del_from + del_len] = b''

    def _choose_block_len(self, max_len: int) -> int:
        """
        模拟AFL的choose_block_len概率分布：
        - 短删除（1-8字节）更高概率（75%）
        - 长删除（最多64字节）较低概率（25%）

        如果 max_len < 8，则强制只使用短块模式。
        """
        if max_len < 1:
            raise ValueError("max_len must be at least 1")

        # 强制限制最大值为 64（符合 AFL 风格）
        max_len = min(max_len, 64)

        r = self._rng.random()

        # 如果 max_len < 8，只能选择短块
        if max_len < 8:
            return self._rng.randint(1, max_len)

        # 否则按照 AFL 概率选择短块或长块
        if r < 0.75:
            return self._rng.randint(1, min(8, max_len))
        else:
            return self._rng.randint(8, max_len)

    def clone_or_insert_block(self, data: bytearray, max_size: int = 1 * 1024 * 1024) -> None:
        """
        克隆或插入字节块（75%概率克隆现有数据，25%概率插入随机值）
        保持AFL的以下特性：
        - 克隆时从原数据中随机选取片段
        - 插入时生成随机值或重复单个字节
        - 总大小不超过max_size（默认1MB）
        """
        if len(data) >= max_size:  # 超过最大限制则不操作
            return

        # 决定是克隆(75%)还是插入新块(25%)
        actually_clone = self._rng.random() < 0.75

        if actually_clone:
            # 克隆现有数据块
            clone_len = self._choose_block_len(len(data))
            clone_from = self._rng.randint(0, len(data) - clone_len)
            block = data[clone_from:clone_from + clone_len]
        else:
            # 生成新块（50%概率用随机字节，50%用重复字节）
            clone_len = self._choose_block_len(64)  # AFL默认最大64字节
            if self._rng.random() < 0.5:
                block = bytes(self._rng.randint(0, 255) for _ in range(clone_len))
            else:
                block = bytes([self._rng.randint(0, 255)] * clone_len)

        # 随机选择插入位置
        clone_to = self._rng.randint(0, len(data))

        # 执行插入/克隆
        data[clone_to:clone_to] = block  # 插入到指定位置


    def overwrite_bytes(self, data: bytearray) -> None:
        """
        合并长度选择的字节覆盖变异函数
        功能：
        - 75%概率复制现有数据块
        - 25%概率用固定值覆盖
        - 自动处理所有边界情况
        """
        if len(data) < 2:
            return

        # 计算最大可用块长度（至少保留1字节）
        max_len = len(data) - 1
        if max_len < 1:
            return

        # 直接内联长度选择逻辑（原choose_block_len）
        if max_len <= 8 or self._rng.random() < 0.75:
            copy_len = self._rng.randint(1, min(8, max_len))
        else:
            copy_len = self._rng.randint(8, max_len)

        # 安全选择位置（捕获所有可能的计算错误）
        try:
            copy_from = self._rng.randint(0, len(data) - copy_len)
            copy_to = self._rng.randint(0, len(data) - copy_len)
        except ValueError:
            return

        # 执行覆盖操作
        if self._rng.random() < 0.75:  # 复制块
            if copy_from != copy_to:  # 避免无操作
                data[copy_to:copy_to+copy_len] = data[copy_from:copy_from+copy_len]
        else:  # 填充固定值
            fill_byte = (self._rng.randint(0, 255) if self._rng.random() < 0.5 
                        else data[self._rng.randint(0, len(data) - 1)])
            data[copy_to:copy_to+copy_len] = bytes([fill_byte] * copy_len)

    def overwrite_with_extra(self, msg: bytearray) -> None:
        """ 用 extras 中的某个条目覆盖 msg 中的部分内容 """
        if not self.extras and not self.a_extras:
            return  # 没有 extras 可用

        # 决定使用哪个 extras 列表
        use_a_extras = not self.extras or (self.a_extras and self._rng.random() < 0.5)

        extra_list = self.a_extras if use_a_extras else self.extras
        extra = self._rng.choice(extra_list)
        extra_len = extra.len

        if extra_len > len(msg):
            return  # extra 太长，无法插入

        insert_at = self._rng.randint(0, len(msg) - extra_len)
        msg[insert_at:insert_at + extra_len] = extra.data

    def insert_with_extra(self, msg: bytearray) -> None:
        """ 向 msg 中插入 extras 中的某个条目 """
        MAX_FILE = 1024 * 1024  # 假设最大文件大小限制为 1MB，可根据需要调整
        if not self.extras and not self.a_extras:
            return  # 没有 extras 可用

        # 决定使用哪个 extras 列表
        use_a_extras = not self.extras or (self.a_extras and self._rng.random() < 0.5)

        extra_list = self.a_extras if use_a_extras else self.extras
        extra = self._rng.choice(extra_list)
        extra_len = extra.len

        if len(msg) + extra_len >= MAX_FILE:
            return  # 超出最大长度限制

        insert_at = self._rng.randint(0, len(msg))
        msg[insert_at:insert_at] = extra.data  # 插入操作

    def overwrite_with_region(self,messages:List[bytearray], msg_idx:int)->None:
        while True:
            other_msg_idx = self._rng.randint(0,len(messages)-1)
            if other_msg_idx != msg_idx:
                break

        messages[msg_idx] = copy.deepcopy(messages[other_msg_idx])

    def insert_with_region(self,messages:List[bytearray], msg_idx:int)->None:
        while True:
            other_msg_idx = self._rng.randint(0, len(messages)-1)
            if other_msg_idx != msg_idx:
                break
        messages.insert(msg_idx,copy.deepcopy(messages[other_msg_idx]))

                                  

    def insert_with_region2(self,messages:List[bytearray], msg_idx:int)->None:
        while True:
            other_msg_idx = self._rng.randint(0, len(messages)-1)
            if other_msg_idx != msg_idx:
                break
        messages.insert(msg_idx+1,copy.deepcopy(messages[other_msg_idx]))

                                  

    def duplicate_region(self,messages:List[bytearray], msg_idx:int)->None:
        messages.insert(msg_idx,copy.deepcopy(messages[msg_idx]))
        messages_len = len(messages) 



class Fuzzer():
    
    def __init__(self, conf_path):
        self.conf_path = conf_path
        with open(conf_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
                
        
        

        self.debug()
        pyafl.parse_args(json.dumps(self.config)
)
        pyafl.set_up()
        
        self.exec_tmout = pyafl.get_exec_tmout()
        self.hang_tmout = 1000

        # 初始化test_cases列表
        self.init_test_cases: List[TestCase] = []
        self.stats:Stats = Stats()
        self.__get_test_cases_from_dir()

        self.init_out_dir()
        self.mutator = Mutator(extras = utils.load_extras_file(self.config['extra']) if 'extra' in self.config else None)
        
        self.running = True
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
        self.MAP_SIZE = 2 ** 16
        self.top_rated = {}
        self.total_exec = 0

        self.current_test_case = self.init_test_cases[0]
        self.favor_test_cases = []
        self.queue = copy.deepcopy(self.init_test_cases)

        self.mutated_messages = None

        self.score_changed = 0
        self.current_queue_idx = 0


        self.KEEP_UNIQUE_HANG = 500
        self.KEEP_UNIQUE_CRASH = 5000
        self.HAVOC_MAX_MULT = 16
        self.SKIP_TO_NEW_PROB = 99 
        self.HAVOC_MIN = 16 # min havoc times
        self.HAVOC_CYCLES_INIT = 1024

        self.total_cal_us = 0
        self.cal_cycles = 0
        self.total_bitmap_size = 0
        self.total_bitmap_entries = 0

        
        self.pending_favored = 0 # Pending favored paths 
        self.havoc_div = 1




    def init_out_dir(self):
        out_parent_dir = self.config['output_dir']
        self.favor_test_cases_dir = os.path.join(out_parent_dir,'favor_test_cases')
        self.queue_dir = os.path.join(out_parent_dir,'queue')
        self.crash_test_cases_dir = os.path.join(out_parent_dir,'crash_test_cases')
        self.tmout_test_cases_dir = os.path.join(out_parent_dir,'tmout_test_cases')

        os.makedirs(self.favor_test_cases_dir,exist_ok=True)
        os.makedirs(self.crash_test_cases_dir,exist_ok=True)
        os.makedirs(self.tmout_test_cases_dir,exist_ok=True)
        os.makedirs(self.queue_dir,exist_ok=True)


        
    def __get_test_cases_from_dir(self) -> None:

        input_dir = self.config["input_dir"]
        
        # 确保输入目录存在
        if not os.path.isdir(input_dir):
            raise FileNotFoundError(f"Input directory not found: {input_dir}")
        
        # 遍历目录下所有文件
        for file_name in os.listdir(input_dir):
            file_path = os.path.join(input_dir, file_name)
            
            # 跳过目录，只处理文件
            if not os.path.isfile(file_path):
                continue
            
            # 读取文件内容
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # 根据协议类型提取消息
            if self.config['protocol'] == "TLS":
                messages = utils.extract_requests_tls(file_content)
                ### for test
                # messages = [bytes(100) for _ in range(5)] 
            else:
                # 其他协议的处理可以在这里扩展
                messages = [bytearray(file_content)]  # 默认整个文件作为一个消息
            
            # 保存到test_cases列表
            self.init_test_cases.append(TestCase(file_path,messages))

    
    def get_init_test_cases(self):
        return self.init_test_cases

    def print_init_test_cases(self) -> None:
        """
        以美观的表格格式打印所有测试用例信息
        
        显示内容包括:
        - 文件序号
        - 文件名
        - 文件大小
        - 消息数量
        - 首条消息预览
        """
        if not hasattr(self, 'test_cases') or not self.init_test_cases:
            print("[yellow]⚠️ 没有可用的测试用例[/yellow]")
            return

        console = Console()
        
        # 创建主表格
        table = Table(
            title="[bold cyan]测试用例概览[/bold cyan]",
            box=ROUNDED,
            header_style="bold magenta",
            title_style="bold",
            show_header=True,
            expand=True
        )
        
        # 添加列
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("文件名", style="green", min_width=20)
        table.add_column("大小", justify="right", style="blue")
        table.add_column("消息数", justify="right", style="yellow")
        table.add_column("首条消息预览", style="dim", min_width=30)

        # 添加数据行
        for idx, case in enumerate(self.init_test_cases, 1):
            file_size = os.path.getsize(case.file_path)
            first_msg = case.messages[0] if case.messages else b''
            
            # 格式化消息预览 (显示前16字节的hex)
            preview = first_msg[:16].hex(' ') + ("..." if len(first_msg) > 16 else "")
            
            table.add_row(
                str(idx),
                case.file_path,
                humanize.naturalsize(file_size),
                str(len(case.messages)),
                preview
            )

        # 创建统计面板
        total_files = len(self.init_test_cases)
        total_messages = sum(len(case.messages) for case in self.init_test_cases)
        stats = Panel(
            f"[b]文件总数:[/b] {total_files}\n"
            f"[b]消息总数:[/b] {total_messages}\n"
            f"[b]输入目录:[/b] {self.config['input_dir']}",
            title="[bold]统计信息[/bold]",
            border_style="blue",
            width=50
        )

        # 打印输出
        console.print(stats)
        console.print(table)
        
        # 添加提示信息
        console.print(
            "[dim]提示: 使用 [bold]get_test_case_detail(index)[/bold] 查看特定用例的详细信息[/dim]",
            justify="center"
        )

    def get_test_case_detail(self, index: int) -> None:
        """
        打印指定测试用例的详细信息
        """
        if not 0 <= index-1 < len(self.init_test_cases):
            print("[red]❌ 无效的索引[/red]")
            return
        
        case = self.init_test_cases[index-1]
        console = Console()
        
        # 创建详细面板
        info = Panel(
            f"[b]路径:[/b] {case.file_path}\n"
            f"[b]大小:[/b] {humanize.naturalsize(os.path.getsize(case.file_path))}\n"
            f"[b]消息数:[/b] {len(case.messages)}",
            title=f"[bold]测试用例 #{index} 详情[/bold]",
            border_style="green"
        )
        
        # 创建消息表格
        msg_table = Table(
            title="[bold]消息列表[/bold]",
            box=ROUNDED,
            show_header=True,
            header_style="bold blue"
        )
        msg_table.add_column("#", style="cyan")
        msg_table.add_column("类型", style="magenta")
        msg_table.add_column("长度", justify="right")
        msg_table.add_column("内容预览", style="dim")
        
        for i, msg in enumerate(case.messages, 1):
            msg_type = "TLS" if self.config['protocol'] == "TLS" else "RAW"
            preview = msg[:16].hex(' ') + ("..." if len(msg) > 16 else "")
            msg_table.add_row(
                str(i),
                msg_type,
                humanize.naturalsize(len(msg)),
                preview
            )
        
        # 打印输出
        console.print(info)
        console.print(msg_table)

    @profile 
    def run_target(self,test_case):

        self.stats.total_exec += 1
        messages = test_case.messages
        timeout = self.exec_tmout  
        response = []

        pyafl.pre_run_target(timeout)


        response.append(pyafl.get_response_buff())
        

        for msg in messages:
            
            pyafl.run_target(bytes(msg))
            response.append(pyafl.get_response_buff())

        
        # pyafl.run_target(messages[0])
        # response.append(pyafl.get_response_buff())
        # pyafl.run_target(messages[1])
        # response.append(pyafl.get_response_buff())
        # pyafl.run_target(messages[2])
        # response.append(pyafl.get_response_buff())
        # pyafl.run_target(messages[3])
        # response.append(pyafl.get_response_buff())
        # pyafl.run_target(messages[4])
        # response.append(pyafl.get_response_buff())


        pyafl.post_run_target(timeout)

        # response.append(pyafl.get_response_buff())
        return messages,response



    def run_target_fast(self, messages, timeout):

        self.stats.total_exec += 1

        response = []

        pyafl.pre_run_target(timeout)
        response.append(pyafl.get_response_buff())
    
        for msg in messages:
            pyafl.run_target(bytes(msg))
            response.append(pyafl.get_response_buff())

        fault = pyafl.post_run_target(timeout)

        return fault


    def profile_run_target(self,test_case):

        profiler = LineProfiler()
        profiler.add_function(self.run_target)  # 添加要分析的函数

        # 运行分析
        profiler.enable_by_count()
        result = self.run_target(test_case)
        profiler.disable_by_count()

        # 打印结果
        profiler.print_stats(output_unit=1e-3)




    def debug(self):
        pyafl.debug()
    
    def clear(self):
        pyafl.clear()

    def calibrate_case(self,test_case:TestCase,handicap = 0):
        
        first_run = not test_case.cksum
        stage_max = 7
        first_trace = None
        fault = FaultCode.NONE

        self.stats.stage_name = "calibration"

        start_time_us = utils.get_cur_time_us()

        for i in range(stage_max):

            self.run_target_fast(test_case.messages,self.exec_tmout)

            if not i and not pyafl.trace_bytes_count():
                fault = FaultCode.NOINST
                return fault

            cksum = pyafl.trace_hash32()

            if test_case.cksum != cksum:

                # 如果test_case.cksum有值且和这次运行不相等，说明两次运行代码覆盖不一致
                if test_case.cksum:
                    test_case.var_behavior = 1

                
                # 说明是第一次运行
                else:
                    test_case.cksum = cksum

    
        stop_time_us = utils.get_cur_time_us()

        self.total_cal_us += stop_time_us - start_time_us
        self.cal_cycles += stage_max

        test_case.exec_us = (stop_time_us - start_time_us) / stage_max
        test_case.bitmap_size = pyafl.trace_bytes_count()
        test_case.handicap = handicap
        test_case.trace_mini_hash = pyafl.trace_min_hash32()


        self.total_bitmap_size += test_case.bitmap_size
        self.total_bitmap_entries += 1



        return fault


    def cull_queue(self,test_case:TestCase):
        flags = 0
        if test_case.trace_mini_hash not in self.top_rated:
            self.top_rated[test_case.trace_mini_hash] = test_case
            flags = 1

            
            
        else:
            pre = self.top_rated[test_case.trace_mini_hash]
            favor_factor = test_case.exec_us * test_case.messages_len
            if favor_factor < pre.exec_us * pre.messages_len:
                self.top_rated[test_case.trace_mini_hash] = test_case
                flags = 1
        
        if flags:
            # self.score_changed = 1
            self.stats.favor_paths += 1
            test_case.favored = 1
            if not test_case.was_fuzzed:
                self.pending_favored += 1
        
        return flags
            








    def perform_dry_run(self):

        for test_case in self.init_test_cases:
            print(f"Attempting dry run with {test_case.file_path}")
            Fault = self.calibrate_case(test_case,0)

            if(test_case.var_behavior):
                print("warning: Instrumentation output varies across runs.")

            # test_case.show_status()
    

    def handle_interrupt(self, signum, frame):
        print("\n[!] 检测到中断信号，正在停止...")
        self.running = False


    def calculate_score(self,test_case:TestCase):
        avg_exec_us = self.total_cal_us / self.cal_cycles
        avg_bitmap_size = self.total_bitmap_size / self.total_bitmap_entries

        exec_us = test_case.exec_us
        bitmap_size = test_case.bitmap_size

        perf_score = (
            10 if exec_us * 0.1 > avg_exec_us else
            25 if exec_us * 0.25 > avg_exec_us else
            50 if exec_us * 0.5 > avg_exec_us else
            75 if exec_us * 0.75 > avg_exec_us else
            300 if exec_us * 4 < avg_exec_us else
            200 if exec_us * 3 < avg_exec_us else
            150 if exec_us * 2 < avg_exec_us else
            100
        )

        perf_score *= (
            3 if bitmap_size * 0.3 > avg_bitmap_size else
            2 if bitmap_size * 0.5 > avg_bitmap_size else
            1.5 if bitmap_size * 0.75 > avg_bitmap_size else
            0.25 if bitmap_size * 3 < avg_bitmap_size else
            0.5 if bitmap_size * 2 < avg_bitmap_size else
            0.75 if bitmap_size * 1.5 < avg_bitmap_size else
            1
        )

        if test_case.handicap >= 4:
            perf_score *= 4
            test_case.handicap -= 4
        elif test_case.handicap:
            perf_score *= 2
            test_case.handicap -= 1
        
        if perf_score > self.HAVOC_MAX_MULT * 100:
            perf_score = self.HAVOC_MAX_MULT * 100
        
        perf_score /= (
            10 if avg_exec_us > 50000 else
            5 if avg_exec_us > 20000 else
            2 if avg_exec_us > 10000 else
            1
        )

        return perf_score






        

    def fuzz_one(self):
        


        if self.pending_favored:
            if self.current_test_case.was_fuzzed:
                if random.randint(0,100) < self.SKIP_TO_NEW_PROB:
                    return 1
        
        self.current_test_case.was_fuzzed = 1
        mutated_messages = copy.deepcopy(self.current_test_case.messages)
        start_fuzz_msg_index = random.randint(0,len(mutated_messages) - 1)
        end_fuzz_msg_index = random.randint(start_fuzz_msg_index,len(mutated_messages) - 1)

        


        perf_score = self.calculate_score(self.current_test_case)

    
        stage_max = int(self.HAVOC_CYCLES_INIT * perf_score / 100 )
        cur_stage = 0
        while cur_stage < stage_max:
            
            mutation_times = random.choice([1,2,4,8,16,32,64,128])
            for i in range(mutation_times):
                msg_index = random.randint(start_fuzz_msg_index,end_fuzz_msg_index)

                self.mutator.mutate(mutated_messages,msg_index)

            cur_stage += 1

        self.common_fuzz_stuff(mutated_messages)

    def choose_test_case(self):
        if self.current_queue_idx +1 == len(self.queue):
            self.stats.queue_cycle += 1
        self.current_queue_idx = (self.current_queue_idx + 1) % len(self.queue)
        self.current_test_case = self.queue[self.current_queue_idx] 

    def fuzz(self):
        print("start fuzzing, WAAAAAAAAAGH!!!")
        start_time = time.time()  # 记录fuzzing开始时间
        last_time = start_time
        last_exec = 0


        
        while self.running:
            
            self.choose_test_case()
            # 运行测试用例并计数
            self.fuzz_one()


            
            # 计算并显示每秒执行速率
            current_time = time.time()
            elapsed = current_time - last_time
            
            # 每秒更新一次统计数据
            if elapsed >= 2.0:
                # 计算当前时段的执行速度
                execs_in_period = self.stats.total_exec - last_exec
                execs_per_second = execs_in_period / elapsed
                
                # 打印速率信息
                print(f"[PERF] Current: {execs_per_second:.1f} execs/sec | "
                    f"Total: {self.stats.total_exec} execs")
                
                # 重置计数器和时间戳
                last_time = current_time
                last_exec = self.stats.total_exec


    def save_if_interesting(self, messages:List[bytearray], fault):
        keeping = 0
        
        if fault == FaultCode.NONE.value:
            hub = pyafl.has_new_bit()
            if not hub:
                return 0
            
            test_case_path = os.path.join(self.queue_dir,f"id:{self.stats.queue_len:06d}.raw")
            self.stats.queue_len += 1

            self.save_intersting_test_case(messages, test_case_path) 
            test_case = TestCase(messages=messages, file_path=test_case_path)
            test_case.depth = self.current_test_case.depth + 1
            if hub == 2 and not test_case.has_new_cov:
                test_case.has_new_cov = 1
                self.stats.queued_with_cov += 1



            self.calibrate_case(test_case,self.stats.queue_cycle)

            is_favor = self.cull_queue(test_case)

            if is_favor:
                test_case_path = os.path.join(self.favor_test_cases_dir,f"id:{self.stats.unique_favors:06d}.raw")
                self.stats.unique_favors += 1

                self.save_intersting_test_case(messages, test_case_path) 


            self.queue.append(test_case)


            keeping = 1



        if fault == FaultCode.TMOUT.value:
            self.stats.total_tmouts += 1
            if self.stats.unique_hangs >= self.KEEP_UNIQUE_HANG:
                return keeping

            if  self.config['dumb_mode'] != "True":
                pyafl.simplify_trace_bits()
                if not pyafl.tmout_has_new_bit():
                    return keeping
            
            self.stats.unique_tmouts += 1
        
            if self.exec_tmout < self.hang_tmout:
                new_fault = self.run_target_fast(messages)
                if new_fault == FaultCode.CRASH:
                    self.save_if_interesting(new_fault)
                if new_fault != FaultCode.TMOUT:
                    return keeping

            self.save_intersting_test_case(messages, os.path.join(self.tmout_test_cases_dir,f"id:{self.stats.unique_hangs:06d}.raw"))

            self.stats.unique_hangs += 1
            self.stats.last_hang_time = datetime.now()


        if fault == FaultCode.CRASH.value:
            self.stats.total_crashes += 1
            if self.stats.unique_crashes >= self.KEEP_UNIQUE_CRASH:
                return keeping
            
            if  self.config['dumb_mode'] != "True":
                pyafl.simplify_trace_bits()
                if not pyafl.tmout_has_new_bit():
                    return keeping

            if not self.stats.unique_crashes:
                pass

            self.save_intersting_test_case(messages, os.path.join(self.crash_test_cases_dir,f"id:{self.stats.unique_crashes:06d}.raw"))
        
            self.stats.unique_crashes += 1

            self.stats.last_crash_time = datetime.time()
            self.stats.last_crash_execs = self.stats.total_execs

        if fault == FaultCode.ERROR.value:
            raise ValueError("Unable to execute target application")
        

        return keeping



        
    def save_intersting_test_case(self ,messages ,path):




        with open(path, 'wb') as f:
            f.write(b"".join(messages))

        pass


    def common_fuzz_stuff(self, messages:List[bytearray]):
        
        fault = self.run_target_fast(messages, self.exec_tmout)

        self.save_if_interesting(messages, fault)
        




    




    @staticmethod 
    def mr_log(messages, responses):
        """
        将已有的消息和响应记录写入日志文件
        
        参数:
            messages: 发送的消息列表
            responses: 对应的响应列表（长度应比messages多1，包含pre-run的响应）
        """
        # 验证输入
        if len(responses) != len(messages) + 1:
            raise ValueError("responses长度应为messages长度+1 (包含prerun响应)")
        
        # 写入日志文件
        with open("session.log", "w") as f:
            f.write("=== Message-Response Debug Log ===\n\n")
            
            # 记录pre-run状态
            f.write("[PRE-RUN INITIAL STATE]\n")
            f.write(f"Response: {responses[0]}\n\n")
            
            # 记录每条消息和响应
            for i, (msg, resp) in enumerate(zip(messages, responses[1:-1]), 1):
                f.write(f"[INTERACTION {i}]\n")
                f.write(f"Sent: {msg}\n")
                f.write(f"Received: {resp}\n\n")
            

            
            # 添加分隔线
            f.write("="*50 + "\n")
            f.write("Log generated at: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))


    # 使用示例
    @staticmethod 
    def save_pcap(messages,responses):
        # 1. 获取原始数据

        # 2. 生成PCAP文件
        pcap_gen = PcapGenerator()
        pcap_gen.save_to_pcap(messages, responses, 'session.pcap')
        
        print(f"调试文件已保存为: session.pcap")
