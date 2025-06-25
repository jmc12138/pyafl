import dpkt
import socket
import time
from datetime import datetime


import re,struct
from typing import List, Tuple, Optional

class PcapGenerator:
    def __init__(self, src_ip='192.168.1.100', dst_ip='192.168.1.101',
                 src_port=12345, dst_port=4433):
        """
        初始化PCAP生成器
        
        参数:
            src_ip: 源IP地址 (客户端)
            dst_ip: 目标IP地址 (服务器)
            src_port: 源端口
            dst_port: 目标端口 (默认TLS 4433)
        """
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.seq = 0
        self.ack = 0
        self.timestamp = int(time.time())

    def _create_tcp_packet(self, data, is_client, flags=dpkt.tcp.TH_PUSH|dpkt.tcp.TH_ACK):
        """创建TCP数据包"""
        eth = dpkt.ethernet.Ethernet()
        if is_client:
            src_ip = self.src_ip
            dst_ip = self.dst_ip
            src_port = self.src_port
            dst_port = self.dst_port
        else:
            src_ip = self.dst_ip
            dst_ip = self.src_ip
            src_port = self.dst_port      
            dst_port = self.src_port     

        ip = dpkt.ip.IP(src=socket.inet_aton(src_ip),
                        dst=socket.inet_aton(dst_ip),
                        p=dpkt.ip.IP_PROTO_TCP)
        tcp = dpkt.tcp.TCP(sport=src_port,
                          dport=dst_port,
                          seq=self.seq,
                          ack=self.ack,
                          flags=flags)
        
        tcp.data = data
        ip.data = tcp
        ip.len += len(tcp.data)
        eth.data = ip
        
        # 更新序列号
        if flags & dpkt.tcp.TH_SYN:
            self.seq += 1
        else:
            self.seq += len(data) if data else 0
        
        return eth

    def save_to_pcap(self, messages, responses, filename='debug.pcap'):
        """
        将消息和响应保存为PCAP文件
        
        参数:
            messages: 发送的消息列表 (bytes列表)
            responses: 接收的响应列表 (bytes列表)
            filename: 输出的PCAP文件名
        """
        # 创建PCAP写入器
        with open(filename, 'wb') as f:
            pcap_writer = dpkt.pcap.Writer(f)
            
            pre_resp = responses[0]
            pcap_writer.writepkt(self._create_tcp_packet(pre_resp, False), ts=self.timestamp)

            # 2. 添加应用数据
            for msg, resp in zip(messages, responses[1:]):


                
                # 客户端发送
                self.timestamp += 0.2
                pcap_writer.writepkt(self._create_tcp_packet(msg, True) , ts=self.timestamp)
                
                # 服务器响应
                self.timestamp += 0.1
                pcap_writer.writepkt(self._create_tcp_packet(resp, False), ts=self.timestamp)
            



def get_cur_time_us():



    """高精度单调时钟（适用于性能分析）"""
    return int(time.perf_counter() * 1_000_000)





def extract_requests_tls( buf: bytes) -> List[bytearray]:
    
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
        messages.append(bytearray(buf[pos:record_end]))
        pos = record_end
    
    # 如果没有找到任何记录，返回整个缓冲区作为单个消息
    if not messages and buf:
        messages.append(buf)
    
    return messages





class Extra:
    def __init__(self, data: bytes):
        self.data = data
        self.len = len(data)
        self.hit = 0






import re
from typing import Optional

def parse_extra_line(line: str, dict_level: int) -> Optional[bytes]:
    line = line.strip()
    if not line or line.startswith('#'):
        return None

    # 匹配 name[@level]="value" 格式
    match = re.match(
        r'^'                          # 行首
        r'([a-zA-Z_][a-zA-Z0-9_\-]*)' # 标签名：以字母或下划线开头，后跟字母、数字、下划线、短横线
        r'(@\d+)?'                    # 可选的 @level 部分
        r'\s*=\s*'                    # 等号，前后允许空格
        r'"((?:[^"\\]|\\.)*)"'        # 引号内的值，支持转义
        r'$',
        line
    )

    if not match:
        raise ValueError(f"Malformed line: {line}")

    label, level_str, value = match.groups()

    # 如果有 level 限制，并且当前等级不够，则跳过该条目
    if level_str:
        level = int(level_str[1:])  # 去掉 '@'
        if level > dict_level:
            return None

    # 处理转义字符
    result = bytearray()
    i = 0
    while i < len(value):
        c = value[i]
        if c == '\\':
            i += 1
            if i >= len(value):
                raise ValueError(f"Invalid escape at end of line: {line}")
            next_c = value[i]
            if next_c == '\\':
                result.append(ord('\\'))
            elif next_c == '"':
                result.append(ord('"'))
            elif next_c == 'x' and i + 2 < len(value):
                hex_str = value[i+1:i+3]
                if all(c in '0123456789abcdefABCDEF' for c in hex_str):
                    result.append(int(hex_str, 16))
                    i += 2
                else:
                    raise ValueError(f"Invalid hex escape in line: {line}")
            else:
                raise ValueError(f"Unsupported escape: \\{next_c} in line: {line}")
        else:
            if ord(c) < 32 or ord(c) >= 128:
                raise ValueError(f"Non-printable character in line: {line}")
            result.append(ord(c))
        i += 1

    return bytes(result)


def load_extras_file(fname: str, dict_level: int = 0, max_dict_file: int = 1024) -> List[Extra]:
    """
    从指定文件中加载 extras 字典。

    :param fname: 字典文件路径
    :param dict_level: 字典等级，用于筛选 @level 条目
    :param max_dict_file: 单个关键字最大长度限制
    :return: 解析后的 extras 列表
    """
    extras = []

    with open(fname, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.rstrip('\n')

            # 去除前后空白 & 注释行
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            try:
                parsed = parse_extra_line(stripped, dict_level)
                if parsed is None:
                    continue
                if len(parsed) > max_dict_file:
                    raise ValueError(f"Keyword too big in line {line_num}, limit is {max_dict_file}")
                extras.append(Extra(parsed))
            except Exception as e:
                raise ValueError(f"Error parsing line {line_num}: {e}")

    return extras