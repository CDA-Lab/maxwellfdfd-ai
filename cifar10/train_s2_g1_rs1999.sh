#!/bin/bash

nohup python -u train.py -a -e 100 -it 10 -k 1000 -sn 2 -g 1 -rm -w -rs 1999 > train_s2_g1.log &