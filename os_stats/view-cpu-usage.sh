#!/bin/bash

grep os_cpu_usage /var/log/os_stats.log |sort -t "," -k1.36,1 |less
