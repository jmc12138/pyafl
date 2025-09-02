#!/usr/bin/env python3
import os
import time
import subprocess
from pathlib import Path
import argparse
from typing import List, Tuple
from tqdm import tqdm

class CoverageCollector:
    def __init__(self, folder: str, pno: int, step: int, covfile: str):
        self.folder = Path(folder)
        self.pno = pno
        self.step = step
        self.covfile = Path(covfile)
        self.testdir = "queue"
        self.replayer = "afl-replay"
        self.openssl_cmd = [
            "./apps/openssl", "s_server",
            "-key", "key.pem",
            "-cert", "cert.pem",
            "-4", "-naccept", "1",
            "-no_anti_replay"
        ]
        
        # Initialize coverage file
        self.covfile.unlink(missing_ok=True)
        self.covfile.touch()
        self._run_gcovr(clear=True)
        with self.covfile.open('a') as f:
            f.write("Time,l_per,l_abs,b_per,b_abs\n")

    def _run_gcovr(self, clear: bool = False) -> Tuple[float, int, float, int]:
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
        
        return (
            float(coverage["lines_per"]),
            int(coverage["lines_abs"]),
            float(coverage["branches_per"]),
            int(coverage["branches_abs"])
        )

    def _run_test_case(self, test_file: Path) -> float:
        """Execute a single test case and return timestamp"""
        # Run replayer in background
        replayer_cmd = [
            self.replayer,
            str(test_file),
            "TLS",
            str(self.pno),
            "100"
        ]
        replayer_proc = subprocess.Popen(
            replayer_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # Run OpenSSL server with timeout
        try:
            subprocess.run(
                ["timeout", "-k", "0", "3s"] + self.openssl_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
        except subprocess.CalledProcessError:
            pass  # Expected timeout

        replayer_proc.wait()
        return test_file.stat().st_mtime

    def collect_coverage(self):
        """Main method to collect coverage data"""
        # Get all .raw test files
        test_files = list(self.folder.glob(f"{self.testdir}/*.raw"))
        
        # Process files with progress bar
        print("Processing test files:")
        for i, test_file in enumerate(tqdm(test_files, desc="Processing"), 1):
            timestamp = self._run_test_case(test_file)
            
            if i % self.step == 0:
                cov_data = self._run_gcovr()
                self._write_coverage(timestamp, *cov_data)

        # Final coverage data if step > 1
        if self.step > 1 and test_files:
            cov_data = self._run_gcovr()
            self._write_coverage(timestamp, *cov_data)

    def _write_coverage(self, timestamp: float, l_per: float, 
                       l_abs: int, b_per: float, b_abs: int):
        """Write coverage data to file"""
        with self.covfile.open('a') as f:
            f.write(f"{timestamp},{l_per},{l_abs},{b_per},{b_abs}\n")

# python3 ./coverage.py 
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", help="Fuzzer result folder")
    parser.add_argument("pno", type=int, help="Port number")
    parser.add_argument("step", type=int, help="Step size for coverage collection")
    parser.add_argument("covfile", help="Path to coverage file")
    
    args = parser.parse_args()
    
    # Change to OpenSSL directory
    os.chdir("/home/ubuntu/experiments/openssl-gcov")
    
    collector = CoverageCollector(args.folder, args.pno, args.step, args.covfile)
    collector.collect_coverage()

if __name__ == "__main__":
    main()