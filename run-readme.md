```

sudo apt-get install graphviz-dev  libcjson-dev 


wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
sudo ./llvm.sh 9
```


sudo echo deb http://apt.llvm.org/bionic/ llvm-toolchain-bionic-11 main >> /etc/apt/sources.list
sudo echo deb-src http://apt.llvm.org/bionic/ llvm-toolchain-bionic-11 main >> /etc/apt/sources.list
sudo apt update
sudo apt upgrade
wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key|sudo apt-key add -
sudo apt install clang-11 llvm-11 llvm-11-dev lldb-11 lld-11 -y
sudo apt install libc++-11-dev libc++abi-11-dev -y
sudo ln -s /usr/bin/clang-11 /usr/bin/clang
sudo ln -s /usr/bin/clang++-11 /usr/bin/clang++
sudo ln -s /usr/bin/llvm-ar-11 /usr/bin/llvm-ar
sudo ln -s /usr/bin/llvm-as-11 /usr/bin/llvm-as
sudo ln -s /usr/bin/llvm-config-11 /usr/bin/llvm-config


    apt-get -y install build-essential \
    clang \
    graphviz-dev \
    git \
    autoconf \
    libgnutls28-dev \
    libssl-dev \
    python3-pip \
    net-tools \
    vim \
    gdb \
    netcat \
    strace \
    wget \
    cmake \
    build-essential \
    libgtk2.0-dev \
   libavcodec-dev \
   libavformat-dev \
   libjpeg-dev \
   libswscale-dev \
   libtiff5-dev \
   libgtk2.0-dev \
   pkg-config \
   unzip 
   
   
   

pip install Cython

rm -rf ./build
python3 setup.py build_ext --inplace --verbose