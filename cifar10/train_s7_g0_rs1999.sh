#!/bin/bash

nohup python -u train.py -a -e 100 -it 10 -k 1000 -ua -sb 1 -ual 0.1 -sn 7 -g 0 -rs 1999 > train_s7_g0.log &