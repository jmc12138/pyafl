PyAFL: When Protocol Fuzzing Meets Python Power

The "Lightweight Version" of AFLNet Designed for Researchers — Say Goodbye to the Torments of C Language, Embrace Python's Efficiency!

We developed this project based on https://github.com/aflnet/aflnet

@inproceedings{AFLNet,
author={Van{-}Thuan Pham and Marcel B{\"o}hme and Abhik Roychoudhury},
title={AFLNet: A Greybox Fuzzer for Network Protocols},
booktitle={Proceedings of the 13rd IEEE International Conference on Software Testing, Verification and Validation : Testing Tools Track},
year={2020},}


🤔 Have You Ever Struggled Like This?

• Spent two months studying AFLNet, finally understanding the essence of state machines, mutation, and feedback

• Countless innovative ideas emerged: state selection algorithms, mutation strategies, energy scheduling...

• But due to unfamiliarity with C language, forced to battle Segment Faults, memory leaks, and pointer errors day and night

• Libraries taken for granted in Python like numpy, pandas, and scikit-learn are unavailable in C

• Spent months implementing ideas only to find poor results, while half your graduate career has passed...

• Next idea? Another few weeks or months of development? Time won't wait!

🎯 PyAFL Was Born for You!

Yes! My friend, yes!

PyAFL fully implements AFLNet's core logic but is built with pure Python, enabling you to:

✨ Core Advantages

• 🐍 Pure Python Implementation - Get started directly without battling C language

• 🔧 Seamless Python Ecosystem Integration - NumPy, Pandas, machine learning libraries ready to use

• ⚡ Rapid Prototype Validation - Validate ideas in days, not months

• 🧠 Focus on Algorithm Innovation - Bid farewell to low-level debugging, focus on core research

• 📊 Rich Data Analysis - Easily record and analyze test results with Jupyter visualization support

• ⚡ Extreme Performance Optimization - Uses Cython to call AFLNet's performance-sensitive code, implements algorithm logic in Python, with performance nearly matching native AFLNet

🚀 Quick Start

Recommend using Docker environment directly for a smoother and safer experience

1. Environment Dependencies

1.1 Install Docker

Docker installation reference:
https://blog.csdn.net/2301_82242351/article/details/138561820

Docker mirror source configuration reference:
https://blog.csdn.net/u014390502/article/details/143472743

Finally, run docker run hello-world - success means installation is complete

1.2 Install VSCode

Download the Dev Containers extension

2. OpenSSL Fuzz Example

2.1 Installation

git clone https://gitee.com/zhangph12138/pyafl-profuzzbench.git

cd pyafl-profuzzbench/TLS/openssl
docker build --progress=plain -t openssl .


2.2 Running

docker run -it openssl bash


Open VSCode. After installing Dev Containers, this icon will appear on the left side (highlighted in red in the image)
!pics/image.png
Click the small arrow next to openssl
!pics/image2.png

Note: Need to run sudo usermod -aG docker $USER to allow regular users to use Docker, otherwise the container might not appear in VSCode

Open the directory /home/ubuntu/pyafl

Start fuzzing:

python3 main.py ./configs/openssl.json


Collect coverage information:

./cov_script.sh /home/ubuntu/experiments/out-openssl-pyafl 4433 50 /home/ubuntu/pyafl/pyafl-openssl.csv


Coverage saved to /home/ubuntu/pyafl/pyafl-openssl.csv

3 How to Extend

To test other protocols:
1 Need to write corresponding config.json

{
    "name": "openssl", # Protocol implementation name
    "protocol": "TLS", # Protocol type
    "skip_deterministic": "True", # Whether to skip deterministic mutation (can be ignored)
    "input_dir": "/home/ubuntu/experiments/in-tls", # Input directory (same as AFLNet)
    "extra": "/home/ubuntu/experiments/tls.dict", # Dictionary (same as AFLNet)
    "output_dir": "/home/ubuntu/experiments/out-openssl-pyafl", # Output directory (output content slightly different)
    "use_net": "tcp://127.0.0.1/4433", # Network usage (same as AFLNet)
    "server_wait": "10000", # Server startup wait time
    "terminate_child": "True", # Whether to kill child processes (leave unchanged if unsure)
    "poll_wait_msecs": "30", # Maximum wait time per polling operation, i.e., max wait time after sending each message
    "exec_tmout": "5000+", # Maximum execution timeout
    "mem_limit": "none", # Memory limit
    "target_cmd": "/home/ubuntu/experiments/openssl/apps/openssl s_server -key /home/ubuntu/experiments/openssl/key.pem -cert /home/ubuntu/experiments/openssl/cert.pem -4 -naccept 1 -no_anti_replay", # Server startup command
    "dumb_mode": "False"
}


2 Need to extend protocols, implement corresponding parsing code. Specifically, add sections in Fuzzer.py. It's simple - you can directly use AI models to convert AFLNet's corresponding C code to Python. (I haven't tested other protocols, so this hasn't been implemented yet)

            # Extract messages based on protocol type
            if self.config['protocol'] == "TLS":
                messages = utils.extract_requests_tls(file_content)


📖 Target Audience

• 🔬 Graduate Students in Security Research - Make research more efficient, graduation smoother

• 🧑💻 Protocol Fuzzing Beginners - Lower learning threshold, faster onboarding

• 🤖 Machine Learning Security Researchers - Easily integrate ML models into fuzzing workflow

• 🛠️ Security Engineers Wanting to Quickly Validate Ideas - Shorten the cycle from idea to validation

💡 Why Choose PyAFL?

"I spent two months understanding AFLNet, and another three months battling C language.

Finally, with PyAFL, I validated my new algorithm idea in just one week.

This is exactly the tool I needed!"

🌟 Project Status

• ✅ AFLNet core functionality fully implemented

• ✅ TLS protocol implementation, OpenSSL case study completed

• ✅ Extensible architecture design

• 🚧 More protocol support under development

• 🚧 Advanced data analysis features under development

TODO

• Implement more protocol case studies

• More user-friendly interface design

🤝 Contributions and Support

Welcome code contributions, ideas, and use case sharing!

Whether submitting Issues, creating Pull Requests, or sharing your research cases,
it's all tremendous support for the project!

⭐ If this project helps you, please give us a Star!
Your support is the greatest motivation for our continued development!

ProtocolFuzzing #Python #AFLNet #CyberSecurity #OpenSourceResearch #GraduationTool