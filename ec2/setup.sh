#!/bin/bash
sudo yum -y update
sudo yum -y install gmp-devel git m4 python-devel openssl-devel gcc flex bison
sudo pip install zfec
wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz
tar -xvzf pbc-0.5.14.tar.gz
pushd pbc-0.5.14
./configure LDFLAGS="-lgmp"
sudo make
sudo make install
sudo ldconfig
echo 'export LD_LIBRARY_PATH=/usr/local/lib' >> /home/ec2-user/.bashrc
source /home/ec2-user/.bashrc
popd
git clone -b 2.7-dev https://github.com/JHUISI/charm.git
mv charm /home/ec2-user
chmod 777 /home/ec2-user/charm
pushd /home/ec2-user/charm
sudo make
sudo make install
sudo ldconfig
popd
git clone -b multiple-processes https://github.com/tyurek/asyncmix.git
mv asyncmix /home/ec2-user
chmod 777 /home/ec2-user/asyncmix