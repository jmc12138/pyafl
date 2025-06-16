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

class FaultCode(Enum):
    """Execution status fault codes"""
    NONE = auto()      # 00 - No error
    TMOUT = auto()     # 01 - Timeout
    CRASH = auto()     # 02 - Crash
    ERROR = auto()     # 03 - Error
    NOINST = auto()    # 04 - No instrumentation detected
    NOBITS = auto()    # 05 - No new bits found


class TestCase:
    def __init__(self,file_path , messages):
        self.file_path = file_path
        self.messages  = messages
        self.cksum =  0       #覆盖率的hash32
        self.bitmap_size = 0
        self.exec_us = 0      #执行时间
        self.file_len = os.path.getsize(file_path)
        self.messages_len = len(messages)
        self.var_behavior = 0 # 多次运行覆盖率是否变化
        
        self.trace_mini = 0



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

class Fuzzer():
    
    def __init__(self, conf_path):
        self.conf_path = conf_path
        with open(conf_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
                
        data_str = json.dumps(self.config)

        self.debug()
        pyafl.parse_args(data_str)
        pyafl.set_up()
        

        self.exec_tmout = pyafl.get_exec_tmout()
        # 初始化test_cases列表
        self.init_test_cases: List[TestCase] = []
        self.__get_test_cases_from_dir()

        self.running = True
        signal.signal(signal.SIGINT, self.handle_interrupt)

        self.top_rated = [] 
        self.total_exec = 0

        
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
                messages = self.extract_requests_tls(file_content)
            else:
                # 其他协议的处理可以在这里扩展
                messages = [file_content]  # 默认整个文件作为一个消息
            
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

    # @profile 
    def run_target(self,test_case):
        messages = test_case.messages
        timeout = self.exec_tmout  
        response = []

        pyafl.pre_run_target(timeout)

        response.append(pyafl.get_response_buff())
        

        for msg in messages:

            pyafl.run_target(msg)
            response.append(pyafl.get_response_buff())

        
        # pyafl.run_target(messages[0])
        # pyafl.run_target(messages[1])
        # pyafl.run_target(messages[2])
        # pyafl.run_target(messages[3])
        # pyafl.run_target(messages[4])

        pyafl.post_run_target(timeout)

        # response.append(pyafl.get_response_buff())
        return messages,response

    def profile_run_target(self,test_case):

        profiler = LineProfiler()
        profiler.add_function(self.run_target)  # 添加要分析的函数

        # 运行分析
        profiler.enable_by_count()
        result = self.run_target(test_case)
        profiler.disable_by_count()

        # 打印结果
        profiler.print_stats()




    def debug(self):
        pyafl.debug()
    
    def clear(self):
        pyafl.clear()

    def calibrate_case(self,test_case:TestCase):

        first_run = not test_case.cksum
        stage_max = 7
        first_trace = None
        fault = FaultCode.NONE

        start_time_us = utils.get_cur_time_us()

        for i in range(stage_max):

            self.run_target(test_case)

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

        test_case.exec_us = (stop_time_us - start_time_us) / stage_max
        test_case.bitmap_size = pyafl.trace_bytes_count()

        
        return fault


    def perform_dry_run(self):

        for test_case in self.init_test_cases:
            print(f"Attempting dry run with {test_case.file_path}")
            Fault = self.calibrate_case(test_case)

            if(test_case.var_behavior):
                print("warning: Instrumentation output varies across runs.")

            # test_case.show_status()
    

    def handle_interrupt(self, signum, frame):
        print("\n[!] 检测到中断信号，正在停止...")
        self.running = False


    def fuzz(self):
        print("start fuzzing, WAAAAAAAAAGH!!!")
        start_time = time.time()  # 记录fuzzing开始时间
        last_time = start_time
        last_exec = 0
        
        while self.running:
            # 运行测试用例并计数
            self.run_target(self.init_test_cases[0])
            self.total_exec += 1
            
            # 计算并显示每秒执行速率
            current_time = time.time()
            elapsed = current_time - last_time
            
            # 每秒更新一次统计数据
            if elapsed >= 1.0:
                # 计算当前时段的执行速度
                execs_in_period = self.total_exec - last_exec
                execs_per_second = execs_in_period / elapsed
                
                # 打印速率信息
                print(f"[PERF] Current: {execs_per_second:.1f} execs/sec | "
                    f"Total: {self.total_exec} execs")
                
                # 重置计数器和时间戳
                last_time = current_time
                last_exec = self.total_exec



    def extract_requests_tls(self, buf: bytes) -> List[bytes]:
        
        """
        从字节缓冲区中提取TLS请求区域
        
        参数:
            buf: 输入的字节缓冲区，包含TLS记录
            
        返回:
            分割后的TLS消息列表，每个元素是一个完整的TLS记录(bytes)
        """
        messages = []
        pos = 0
        buf_size = len(buf)
        
        while pos + 5 <= buf_size:  # 至少需要5字节的TLS记录头
            # 解析TLS记录头
            content_type = buf[pos]
            version = buf[pos+1:pos+3]
            length = struct.unpack('!H', buf[pos+3:pos+5])[0]
            
            # 检查是否有足够的字节完成这个记录
            record_end = pos + 5 + length
            if record_end > buf_size:
                # 不完整的记录，将其余部分作为一个消息
                messages.append(buf[pos:])
                break
            
            # 提取完整的TLS记录
            messages.append(buf[pos:record_end])
            pos = record_end
        
        # 如果没有找到任何记录，返回整个缓冲区作为单个消息
        if not messages and buf:
            messages.append(buf)
        
        return messages
    




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
