#!/usr/bin/env python
#

# Each line is a single record to be added to the database. The records are
# timestamped using the syslog time stamp, the "host" value comes from the
# syslog source host field, and the rest of the data is a csv formatted string.

# In theory the primary key for the tables should be (tstamp, uuid) and
# (tstamp, host), but initially no primary keys have been defined.

import os
import sys
import sqlite3
from datetime import datetime as dt
import time
import argparse

logfile="/var/log/os_stats.log"
dbfile="./test_stats.sqlite3"

log = open(logfile, "r")
db = sqlite3.connect(dbfile)
c = db.cursor()

def process_aggregate(data, tstamp, host):
	if tstamp < last_host_tstamp:
		return
	# the data fields are: host, vcpus, wall time, cpu time, derived efficiency
	(_, vcpus, wall_time, cpu_time, eff) = data.split(',')

	print "insert into host_stats values (%d, %s, %d, %d, %f)" % (int(tstamp), host, int(vcpus), int(wall_time), float(cpu_time))
	c.execute("insert into host_stats values (?, ?, ?, ?, ?)", (int(tstamp), host, int(vcpus), int(wall_time), float(cpu_time)))

def process_instance(data, tstamp, host):
	if tstamp < last_instance_tstamp:
		return
	(uuid, _, vcpus, wall_time, _, cpu_time, _) = data.split(',')

	print "insert into instance_stats values (%d, %s, %s, %d, %d, %f)" % (int(tstamp), uuid, host, int(vcpus), int(wall_time), float(cpu_time))
	c.execute("insert into instance_stats values (?, ?, ?, ?, ?, ?)",  (int(tstamp), uuid, host, int(vcpus), int(wall_time), float(cpu_time)))

c.execute("select max(tstamp) from instance_stats")
last_host_tstamp = float(c.fetchone()[0])
c.execute("select max(tstamp) from host_stats")
last_instance_tstamp = float(c.fetchone()[0])

for line in log:
	tstamp = time.mktime(dt.strptime(line[0:15]+" 2015", "%b %d %X %Y").timetuple())
#	print tstamp
	
	(host, rtype, data) = line[16:].split()
	if rtype == "os_cpu_aggregate:":
		process_aggregate(data, tstamp, host)
	elif rtype == "os_cpu_usage:":
		process_instance(data, tstamp, host)
	else:
		print "Unknown record type"
	
db.commit()
db.close()
