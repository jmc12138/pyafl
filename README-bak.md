./cov_script.sh /home/ubuntu/experiments/out-openssl-pyafl 4433 500 /home/ubuntu/pyafl/pyafl_cov.csv

./cov_script.sh /home/ubuntu/experiments/out-openssl-aflnet 4433 500 /home/ubuntu/pyafl/aflnet_cov.csv


# 完整命令（适合复制粘贴）
/home/ubuntu/aflnwe/afl-fuzz -d -i /home/ubuntu/experiments/in-tls -x /home/ubuntu/experiments/tls.dict -o /home/ubuntu/experiments/out-openssl-aflnwe -N tcp://127.0.0.1/4433 -D 10000 -K -W 30 -t 5000+ -m none -- /home/ubuntu/experiments/openssl/apps/openssl s_server -key /home/ubuntu/experiments/openssl/key.pem -cert /home/ubuntu/experiments/openssl/cert.pem -4 -naccept 1 -no_anti_replay


/home/ubuntu/aflnet/afl-fuzz -d -i /home/ubuntu/experiments/in-tls -x /home/ubuntu/experiments/tls.dict -o /home/ubuntu/experiments/out-openssl-aflnwe -N tcp://127.0.0.1/4433 -D 10000 -P TLS -q 3 -s 3 -K -W 30 -t 5000+ -m none -- /home/ubuntu/experiments/openssl/apps/openssl s_server -key /home/ubuntu/experiments/openssl/key.pem -cert /home/ubuntu/experiments/openssl/cert.pem -4 -naccept 1 -no_anti_replay
