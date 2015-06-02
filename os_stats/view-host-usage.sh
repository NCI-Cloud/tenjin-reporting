#!/bin/bash

grep os_cpu_aggregate /var/log/os_stats.log |sort -k4,4 |less
