import random
from typing import List, Tuple

class TestCase:
    def __init__(self, file_path, messages):
        self.file_path = file_path
        self.messages = messages
        self.messages_len = len(messages)

    def splice_msgs(self, msg1: List[bytearray], candidate_msg2s: List[List[bytearray]]) -> Tuple[bool, List[bytearray]]:
        """
        跨消息字节级拼接：
        1. 将 msg1 和 msg2 视为全局字节流
        2. 找出全局字节差异区间 [start_byte, end_byte]
        3. 在差异区间内随机选一个全局拼接点
        4. 生成新序列：msg1 前半 + msg2 后半（在字节级别）
        """
        if not msg1 or not candidate_msg2s:
            return False, []

        # 预计算 msg1 的总字节和消息边界
        total1 = bytearray()
        offsets1 = [0]  # 每个消息的起始偏移
        for m in msg1:
            total1.extend(m)
            offsets1.append(len(total1))

        MAX_RETRIES = 15
        attempts = 0

        while attempts < MAX_RETRIES:
            attempts += 1
            msg2 = random.choice(candidate_msg2s)
            if not msg2:
                continue

            # 构建 msg2 的总字节流
            total2 = bytearray()
            offsets2 = [0]
            for m in msg2:
                total2.extend(m)
                offsets2.append(len(total2))

            total_len = max(len(total1), len(total2))
            if total_len == 0:
                continue

            # === Step 1: 找全局字节差异起点 ===
            start_byte = 0
            min_len = min(len(total1), len(total2))
            while start_byte < min_len and total1[start_byte] == total2[start_byte]:
                start_byte += 1

            if start_byte == min_len and len(total1) == len(total2):
                continue  # 完全相同

            # === Step 2: 找全局字节差异终点 ===
            end_byte = total_len - 1
            while end_byte >= start_byte:
                b1 = total1[end_byte] if end_byte < len(total1) else None
                b2 = total2[end_byte] if end_byte < len(total2) else None
                if b1 != b2:
                    break
                end_byte -= 1

            if end_byte < start_byte:
                continue

            # 差异字节数至少为 2？
            if end_byte - start_byte < 1:
                continue

            # === Step 3: 在 [start_byte, end_byte] 内随机选拼接点 ===
            splice_byte = start_byte + random.randint(0, end_byte - start_byte)

            # === Step 4: 找到 splice_byte 在 msg1 和 msg2 中对应的消息索引和偏移 ===
            # 在 msg1 中定位
            msg1_idx = 0
            while msg1_idx < len(offsets1) - 1 and offsets1[msg1_idx + 1] <= splice_byte:
                msg1_idx += 1
            if msg1_idx >= len(msg1):
                msg1_idx = len(msg1) - 1

            # 在 msg2 中定位
            msg2_idx = 0
            while msg2_idx < len(offsets2) - 1 and offsets2[msg2_idx + 1] <= splice_byte:
                msg2_idx += 1
            if msg2_idx >= len(msg2):
                msg2_idx = len(msg2) - 1

            # 计算在各自消息中的偏移
            byte_offset_in_msg1 = splice_byte - offsets1[msg1_idx] if msg1_idx < len(offsets1) - 1 else splice_byte - offsets1[-2]
            byte_offset_in_msg2 = splice_byte - offsets2[msg2_idx] if msg2_idx < len(offsets2) - 1 else splice_byte - offsets2[-2]

            # 限制偏移不越界
            byte_offset_in_msg1 = max(0, min(byte_offset_in_msg1, len(msg1[msg1_idx])))
            byte_offset_in_msg2 = max(0, min(byte_offset_in_msg2, len(msg2[msg2_idx])))

            # === Step 5: 构造新消息序列 ===
            result = []

            # 1. 添加 msg1 中拼接点之前的所有完整消息
            for i in range(msg1_idx):
                result.append(bytearray(msg1[i]))

            # 2. 构造混合消息（msg1[msg1_idx] 前半 + msg2[msg2_idx] 后半）
            part1 = msg1[msg1_idx][:byte_offset_in_msg1]
            part2 = msg2[msg2_idx][byte_offset_in_msg2:]
            mixed_msg = bytearray(part1 + part2)
            result.append(mixed_msg)

            # 3. 添加 msg2 中拼接点之后的所有完整消息
            for i in range(msg2_idx + 1, len(msg2)):
                result.append(bytearray(msg2[i]))

            return True, result

        return False, []

    

msg1 = [
    bytearray(b"GET /"),
    bytearray(b"Host: a.com")
]

msg2 = [
    bytearray(b"GET /index.html"),
    bytearray(b"Host: b.com")
]

# total1 = b"GET /Host: a.com"
# total2 = b"GET /index.htmlHost: b.com"
# 差异从字节 5 开始（'/' vs 'i'），到末尾
# 假设 splice_byte = 8 → 落在 msg1[1] 和 msg2[1] 中
# result[0] = msg1[0] = b"GET /"
# mixed = msg1[1][:3] + msg2[1][3:] = b"Hos" + b"t: b.com" → b"HoSt: b.com"
# result[1] = mixed
# result[2] = msg2[1] 之后的消息（无）