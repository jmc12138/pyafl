
推荐在docker中使用


1. install pyafl 


pip install -r ./requirements.txt

rm -rf ./build
python3 setup.py build_ext --inplace --verbose


2. 运行

python3 main.py ./configs/openssl.json


3. 分析覆盖率

./cov_script.sh /home/ubuntu/experiments/out-openssl-pyafl 4433 50 /home/ubuntu/pyafl/pyafl-openssl.csv




