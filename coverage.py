#!/usr/bin/env python3
import os
import sys
import time
import subprocess
from pathlib import Path
import pandas as pd
import json
from tqdm import tqdm
import logging

# 配置日志输出
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CoverageCollector:
    def __init__(self, folder, port, step, covfile, target_cmd: str, work_dir):
        self.folder = Path(folder)
        self.port = port
        self.step = step
        self.covfile = Path(covfile)
        self.coverage_data = []
        self.skipped_log = []  # 记录跳过的测试用例
        # Determine test directory and replayer
        self.testdir = "queue" 
        self.replayer = "aflnet-replay" 
        self.target_cmd = target_cmd.split(' ')
        self.work_dir = work_dir
        os.chdir(work_dir)

    def initialize(self):
        """Initialize coverage file and clear gcov data"""
        self.covfile.unlink(missing_ok=True)
        self.covfile.touch()
        self._run_gcovr(clear=True)
        
        # Write CSV header
        with self.covfile.open('a') as f:
            f.write("Time,l_per,l_abs,b_per,b_abs\n")

    def _run_gcovr(self, clear=False):
        """Run gcovr and return coverage data"""
        cmd = ["gcovr", "-r", ".", "-s"]
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

    def _run_test_case(self, test_file):
        """运行单个测试用例，捕获超时和其他异常"""
        replayer_cmd = [self.replayer, str(test_file), "TLS", str(self.port), "100"]
        proc = subprocess.Popen(replayer_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        try:
            result = subprocess.run(
                self.target_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10
            )
            if result.returncode != 0:
                logging.warning(f"Test case {test_file} exited with code {result.returncode}.")
        except subprocess.TimeoutExpired:
            logging.warning(f"Test case {test_file} timed out. Skipping.")
            self.skipped_log.append(str(test_file))
        except Exception as e:
            logging.error(f"Unexpected error with test case {test_file}: {e}")
            self.skipped_log.append(str(test_file))
        finally:
            # 确保 replayer 进程完成
            proc.wait()

    def process_files(self):
        """Process all test files and collect coverage"""
        test_dir = self.folder / self.testdir
        
        id_files = list(test_dir.glob("id*"))
        total_files = len(id_files)
        
        with tqdm(total=total_files, desc="Processing test cases", unit="file") as pbar:
            count = 0
            for test_file in id_files:
                count += 1
                self._process_single_test(
                    test_file,
                    record=(count % self.step == 0)
                )
                pbar.update(1)
            
            if not count % self.step:
                self.save_coverage()

            # Record last test case if step > 1
            if self.step > 1 and count % self.step != 0:
                self._record_coverage(test_file)

    def _process_single_test(self, test_file, record):
        """Process a single test file"""
        self._run_test_case(test_file)
        
        if record:
            self._record_coverage(test_file)

    def _record_coverage(self, test_file):
        """Record coverage data for a test file"""
        timestamp = test_file.stat().st_mtime
        coverage = self._run_gcovr()
        
        if coverage:
            self.coverage_data.append({
                "Time": timestamp,
                "l_per": coverage["lines_per"],
                "l_abs": coverage["lines_abs"],
                "b_per": coverage["branches_per"],
                "b_abs": coverage["branches_abs"]
            })

    def save_coverage(self):
        """Save collected coverage data to CSV"""
        if not self.coverage_data:
            print("Warning: No coverage data collected", file=sys.stderr)
            return

        try:
            df = pd.DataFrame(self.coverage_data)
            df.to_csv(self.covfile, mode='a', header=False, index=False)
            self.coverage_data.clear()  # 清空已保存数据
        except Exception as e:
            print(f"Error saving coverage data: {str(e)}", file=sys.stderr)

    def save_skipped_log(self, log_path="skipped_tests.log"):
        """将跳过的测试用例写入日志文件"""
        if self.skipped_log:
            with open(log_path, 'w') as f:
                for test in self.skipped_log:
                    f.write(f"{test}\n")
            logging.info(f"Skipped {len(self.skipped_log)} test cases. See '{log_path}' for details.")
        else:
            logging.info("No skipped test cases.")


def main():
    conf_path = 'conf.json'

    with open(conf_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    out_dir = config['output_dir']
    covfile_path = os.path.join(out_dir, 'coverage.csv')
    step = config['coverage']['step']
    target_cmd = config['coverage']['target_cmd']
    work_dir = config['coverage']['work_dir']
    
    collector = CoverageCollector(
        folder=out_dir,
        port=4433,
        step=step,
        covfile=covfile_path,
        target_cmd=target_cmd,
        work_dir=work_dir
    )

    print("Initializing coverage collection...")
    collector.initialize()
    
    print("Processing test files...")
    collector.process_files()
    
    print("Saving coverage data...")
    collector.save_coverage()

    print("Saving skipped tests log...")
    collector.save_skipped_log()
    
    print("Coverage collection completed!")

if __name__ == "__main__":
    main()