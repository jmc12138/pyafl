# PyAFL: When Protocol Fuzzing Meets the Power of Python

> **The "Youth Edition" of AFLnet, crafted for researchers — Say goodbye to the pain of C and embrace the efficiency of Python!**
---

[中文文档](README-zh.md) | [English Documentation](README.md)

---

We developed based on [aflnet](https://github.com/aflnet/aflnet)

```
@inproceedings{AFLNet,
author={Van{-}Thuan Pham and Marcel B{\"o}hme and Abhik Roychoudhury},
title={AFLNet: A Greybox Fuzzer for Network Protocols},
booktitle={Proceedings of the 13rd IEEE International Conference on Software Testing, Verification and Validation : Testing Tools Track},
year={2020},}
```

## 🤔 Have You Ever Struggled Like This?

- You spent two months deeply studying **AFLnet**, finally grasping the essence of state machines, mutation, and feedback
- Countless improvement ideas spark in your mind: **state selection algorithms**, **mutation strategies**, **energy scheduling**...
- But due to unfamiliarity with C, you're forced into daily battles with **Segmentation Faults**, **memory leaks**, and **pointer errors**
- Libraries you take for granted in Python — `numpy`, `pandas`, `scikit-learn` — are nowhere to be found in C
- You spend months implementing your idea, only to find it ineffective, while **half your graduate studies have already passed**
- Next idea? Another weeks or months of development? **Time is running out!**

## 🎯 PyAFL Was Born for You!

**Yes! Brother, yes!**

**PyAFL** fully implements the core logic of AFLnet, but built entirely in **pure Python**, allowing you to:

### ✨ Core Advantages
- 🐍 **Pure Python Implementation** – Get started immediately, no need to fight with C
- 🔧 **Seamless Integration with Python Ecosystem** – Plug-and-play with NumPy, Pandas, machine learning libraries
- ⚡ **Rapid Prototyping** – Validate ideas in days, not months
- 🧠 **Focus on Algorithm Innovation** – No more low-level debugging; focus on core research
- 📊 **Rich Data Analysis** – Easily record and analyze test results, with Jupyter visualization support
- ⚡ **Extreme Performance Optimization** – Use Cython to call performance-critical AFLNet code, while implementing algorithmic logic in Python, achieving performance nearly on par with native AFLNet

## 🚀 Quick Start
We recommend using the Docker environment for a smoother and safer experience.

### 1. Environment Dependencies

#### 1.1 Install Docker

For Docker installation, refer to:  
https://blog.csdn.net/2301_82242351/article/details/138561820

For Docker mirror acceleration, refer to:  
https://blog.csdn.net/u014390502/article/details/143472743

Finally, run `docker run hello-world`. If successful, installation is complete.

#### 1.2 Install VSCode

Install the **Dev Containers** extension.

### 2. Example: Fuzzing OpenSSL

#### 2.1 Installation
```
git clone https://gitee.com/zhangph12138/pyafl-profuzzbench.git

cd pyafl-profuzzbench/TLS/openssl
docker build --progress=plain -t openssl .
```

#### 2.2 Run
```
docker run -it openssl bash
```

After installing the Dev Containers extension in VSCode, a red-framed icon will appear on the left sidebar  
![alt text](pics/image.png)  
Click the small arrow next to "openssl"  
![alt text](pics/image2.png)

**Note: Run `sudo usermod -aG docker $USER` to allow regular users to use Docker, otherwise the container may not appear in VSCode.**

Open the directory `/home/ubuntu/pyafl`

Start fuzzing:
```
python3 main.py ./configs/openssl.json
```

Collect coverage information:
```
./cov_script.sh /home/ubuntu/experiments/out-openssl-pyafl 4433 50 /home/ubuntu/pyafl/pyafl-openssl.csv
```
Coverage data will be saved to `/home/ubuntu/pyafl/pyafl-openssl.csv`.

### 3. How to Extend

To test other protocols:

1. Write a corresponding `config.json` file:

```json
"name": "openssl",                   // Name of the protocol implementation
"protocol": "TLS",                   // Protocol type
"skip_deterministic": "True",        // Whether to skip deterministic mutations (can be ignored)
"input_dir": "/home/ubuntu/experiments/in-tls",  // Input directory, same as in AFLnet
"extra": "/home/ubuntu/experiments/tls.dict",    // Dictionary file, same as in AFLnet
"output_dir": "/home/ubuntu/experiments/out-openssl-pyafl",  // Output directory, output content slightly modified
"use_net": "tcp://127.0.0.1/4433",  // Network usage, same as in AFLnet
"server_wait": "10000",              // Wait time for server startup (in milliseconds)
"terminate_child": "True",           // Whether to kill child processes (leave unchanged if unsure)
"poll_wait_msecs": "30",             // Maximum wait time per polling operation, i.e., max wait after sending each message
"exec_tmout": "5000+",               // Maximum execution timeout (in milliseconds), '+' indicates soft timeout
"mem_limit": "none",                 // Memory limit (set to "none" for no limit)
"target_cmd": "/home/ubuntu/experiments/openssl/apps/openssl s_server -key /home/ubuntu/experiments/openssl/key.pem -cert /home/ubuntu/experiments/openssl/cert.pem -4 -naccept 1 -no_anti_replay",  // Command to start the target server
"dumb_mode": "False"                 // Whether to run in dumb mode (no feedback from instrumentation)
```

2. Extend protocol support by adding corresponding parsing code in `Fuzzer.py`. It's simple — you can even use a large language model to convert AFLnet's C code to Python. I haven't tested other protocols, so this isn't implemented yet.

```python
            # Extract messages based on protocol type
            if self.config['protocol'] == "TLS":
                messages = utils.extract_requests_tls(file_content)
```

## 📖 Target Audience

- 🔬 **Graduate Students in Security Research** – Make research more efficient and graduation smoother
- 🧑‍💻 **Beginners in Protocol Fuzzing** – Lower learning curve, faster onboarding
- 🤖 **Machine Learning & Security Researchers** – Easily integrate ML models into fuzzing workflows
- 🛠️ **Security Engineers Wanting Rapid Idea Validation** – Shorten the cycle from idea to validation

## 💡 Why Choose PyAFL?

> "I spent two months understanding AFLnet and three months battling C.  
> Finally, I validated my new algorithm idea in **one week** using PyAFL.  
> This is exactly the tool I needed!"

## 🌟 Project Status

- ✅ Core functionalities of AFLnet fully implemented
- ✅ TLS protocol support and OpenSSL example implemented
- ✅ Extensible architecture design
- 🚧 More protocol support under development
- 🚧 Advanced data analysis features in development

## TODO

- Implement more protocol examples
- Develop more user-friendly interface

## 🤝 Contribution and Support

**We welcome code contributions, idea proposals, and use case sharing!**

Whether you submit an Issue, open a Pull Request, or share your research case,  
your support means a lot to the project!

---

**⭐ If this project helps you, please give us a Star!**  
**Your support is our greatest motivation to keep developing!**

---

#protocol-fuzzing #Python #AFLnet #cybersecurity #open-source-research #graduation-tool