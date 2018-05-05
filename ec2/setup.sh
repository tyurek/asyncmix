#!/bin/bash

# AVSS setup
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

# Viff setup
sudo yum -y install git gcc gmp-devel git
sudo pip install twisted[tls]
sudo pip install gmpy
sudo pip uninstall -y pyasn1
sudo easy_install pyasn1
git clone -b asyncmix https://github.com/amiller/viff/
mv viff/ /home/ec2-user
pushd /home/ec2-user/viff
python setup.py install --home=/home/ec2-user/opt
echo 'export PYTHONPATH=$PYTHONPATH:/home/ec2-user/opt/lib/python' \
	>> /home/ec2-user/.bashrc
source /home/ec2-user/.bashrc
popd