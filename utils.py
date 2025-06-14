import dpkt
import socket
import time
from datetime import datetime

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