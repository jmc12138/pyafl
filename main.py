import argparse
import json
from Fuzzer import Fuzzer

def main():
    # 创建参数解析器
    parser = argparse.ArgumentParser(description='Run the fuzzer with specified configuration')
    parser.add_argument('config', help='Path to the configuration JSON file')
    
    # 解析参数
    args = parser.parse_args()
    
    try:
        # 初始化fuzzer
        fuzzer = Fuzzer(args.config)
        
        # 执行fuzzing流程
        fuzzer.perform_dry_run()
        fuzzer.fuzz()
        fuzzer.clear()
        
        print("Fuzzing completed successfully.")
    except Exception as e:
        print(f"Error occurred during fuzzing: {str(e)}")
        raise


# python3 main.py ./configs/openssl.json
if __name__ == "__main__":
    main()


    