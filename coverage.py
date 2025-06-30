#!/usr/bin/env python3
import os
import sys
import time
import signal
import socket
import subprocess
from pathlib import Path
import pandas as pd
import json
from tqdm import tqdm
import logging
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('coverage.log'),
        logging.StreamHandler()
    ]
)

class CoverageCollector:
    def __init__(self, folder, port, step, covfile, target_cmd: str, work_dir, parallel=False):
        self.folder = Path(folder)
        self.base_port = port
        self.step = step
        self.covfile = Path(covfile)
        self.coverage_data = []
        self.skipped_log = []
        self.testdir = "queue"
        self.replayer = "aflnet-replay"
        self.target_cmd = target_cmd
        self.work_dir = work_dir
        self.parallel = parallel
        self.lock = threading.Lock()
        self.port_lock = threading.Lock()
        self.used_ports = set()
        os.chdir(work_dir)

    def initialize(self):
        """Initialize coverage file and clear gcov data"""
        self.covfile.unlink(missing_ok=True)
        self.covfile.touch()
        self._run_gcovr(clear=True)
        
        with self.covfile.open('a') as f:
            f.write("Time,l_per,l_abs,b_per,b_abs\n")

    def _run_gcovr(self, clear=False):
        cmd = ["gcovr", "-r", ".", "-s", "--gcov-ignore-parse-errors"]
        if clear:
            cmd.append("-d")
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return None

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"gcovr failed: {result.stderr}")

        coverage = {}
        for line in result.stdout.splitlines():
            if line.startswith(("lines", "branch")):
                parts = line.split()
                metric = parts[0].rstrip(':')
                coverage[f"{metric}_per"] = parts[1].rstrip('%')
                coverage[f"{metric}_abs"] = parts[2].lstrip('(').rstrip(')')
        return coverage

    def _get_available_port(self):
        """动态获取可用端口"""
        with self.port_lock:
            for port in range(self.base_port, self.base_port + 100):
                if port not in self.used_ports:
                    if self._port_available(port):
                        self.used_ports.add(port)
                        return port
            raise RuntimeError("No available ports")

    def _port_available(self, port):
        """检查端口是否真正可用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0

    def _release_port(self, port):
        """释放端口"""
        with self.port_lock:
            if port in self.used_ports:
                self.used_ports.remove(port)




    def _run_test_case(self, test_file):
        port = None
        ssl_server = None
        proc = None
        
        try:
            # 1. 获取可用端口
            port = self._get_available_port()
            cmd = self.target_cmd.replace('@@', str(port))
            cmd_list = cmd.split(' ')
            
            # 2. 启动OpenSSL服务器（带调试参数）
            ssl_server = subprocess.Popen(
                cmd_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
                      
            # 4. 运行aflnet-replay（带详细日志）
            replayer_cmd = [
                self.replayer,
                str(test_file),
                "TLS",
                str(port),
                "100"
            ]
            
            proc = subprocess.Popen(
                replayer_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )           

                
        except subprocess.TimeoutExpired:
            error_msg = f"Timeout while processing {test_file} (port:{port})"
            logging.error(error_msg)
            raise RuntimeError(error_msg)
            
        except Exception as e:
            logging.error(f"Unexpected error processing {test_file}: {str(e)}", exc_info=True)
            raise
        finally:
            # 7. 资源清理（跨平台兼容）
            try:
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1)
                    except:
                        if sys.platform != "win32":
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                
                if ssl_server and ssl_server.poll() is None:
                    ssl_server.terminate()
                    try:
                        ssl_server.wait(timeout=1)
                    except:
                        if sys.platform != "win32":
                            os.killpg(os.getpgid(ssl_server.pid), signal.SIGKILL)
                            
                if port:
                    self._release_port(port)
                    
            except Exception as cleanup_err:
                logging.warning(f"Cleanup error: {str(cleanup_err)}")



    def _wait_for_port(self, port, timeout=5):
        """等待端口变为可连接状态"""
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                with socket.create_connection(('localhost', port), timeout=1):
                    return True
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(0.1)
        return False

    def process_files(self):
        test_dir = self.folder / self.testdir
        id_files = sorted(test_dir.glob("id*"))
        total_files = len(id_files)
        
        if self.parallel and '@@' in self.target_cmd:
            # 并行处理（动态端口分配）
            max_workers = min(8, multiprocessing.cpu_count())  # 限制最大并发数
            completed = 0
            
            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Worker") as executor:
                futures = {executor.submit(self._process_single_test, f, i): f 
                          for i, f in enumerate(id_files, 1)}
                
                with tqdm(total=total_files, desc="Processing") as pbar:
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logging.error(f"Thread error: {str(e)}")
                        finally:
                            completed += 1
                            if completed % self.step == 0:
                                self.save_coverage()
                            pbar.update(1)
        else:
            # 顺序处理（固定端口）
            with tqdm(total=total_files, desc="Processing") as pbar:
                for i, test_file in enumerate(id_files, 1):
                    self._process_single_test(test_file, i)
                    pbar.update(1)
        
        # 最终保存
        self.save_coverage()

    def _process_single_test(self, test_file, count):
        """处理单个测试用例（线程安全）"""
        try:
            self._run_test_case(test_file)
            
            if count % self.step == 0:
                with self.lock:
                    self._record_coverage(test_file)
        except Exception as e:
            logging.error(f"Failed {test_file}: {str(e)}")
            self.skipped_log.append(str(test_file))

    def _record_coverage(self, test_file):
        """记录覆盖率数据（线程安全）"""
        coverage = self._run_gcovr()
        if coverage:
            timestamp = test_file.stat().st_mtime
            self.coverage_data.append({
                "Time": timestamp,
                "l_per": coverage["lines_per"],
                "l_abs": coverage["lines_abs"],
                "b_per": coverage["branches_per"],
                "b_abs": coverage["branches_abs"]
            })

    def save_coverage(self):
        """保存覆盖率数据（线程安全）"""
        with self.lock:
            if not self.coverage_data:
                return
            
            try:
                df = pd.DataFrame(self.coverage_data)
                df.to_csv(self.covfile, mode='a', header=False, index=False)
                self.coverage_data.clear()
            except Exception as e:
                logging.error(f"Save failed: {str(e)}")

    def save_skipped_log(self, log_path="skipped_tests.log"):
        """保存跳过的测试用例"""
        if self.skipped_log:
            with open(log_path, 'w') as f:
                f.write("\n".join(self.skipped_log))
            logging.info(f"Saved {len(self.skipped_log)} skipped cases to {log_path}")

def main():
    try:
        with open('conf.json') as f:
            config = json.load(f)
        
        collector = CoverageCollector(
            folder=config['output_dir'],
            port=4433,
            step=config['coverage']['step'],
            covfile=os.path.join(config['output_dir'], 'coverage.csv'),
            target_cmd=config['coverage']['target_cmd'],
            work_dir=config['coverage']['work_dir'],
            parallel=config['coverage'].get('parrallel', 'False').lower() == 'true'
        )

        logging.info("Initializing...")
        collector.initialize()
        
        logging.info("Processing test files...")
        collector.process_files()
        
        logging.info("Saving results...")
        collector.save_skipped_log()
        
        logging.info("Coverage collection completed!")
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

    