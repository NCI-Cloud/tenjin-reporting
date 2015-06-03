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

# defaults
logfile="/var/log/os_stats.log"
dbfile="/root/reporting/os_stats/test_stats.sqlite3"

class LogParser:
	def __init__(self, db, args):
		self.db = db
		self.verbose = args.verbose
		self.dry_run = args.dry_run
		self.stats = args.stats
		self.last_host_tstamp = 0.0
		self.last_instance_tstamp = 0.0

		self.cursor = db.cursor()
		self.cursor.execute("select max(tstamp) from instance_stats")
		tstamp = self.cursor.fetchone()[0]
		if tstamp:
			self.last_host_tstamp = float(tstamp)
		self.cursor.execute("select max(tstamp) from host_stats")
		tstamp = self.cursor.fetchone()[0]
		if tstamp:
			self.last_instance_tstamp = float(tstamp)
		self.cursor.execute("select count(*) from instance_stats")
		self.instance_recs = int(self.cursor.fetchone()[0])
		self.cursor.execute("select count(*) from host_stats")
		self.host_recs = int(self.cursor.fetchone()[0])

		self.insert_count = 0
		self.skip_count = 0

	def commit(self):
		self.db.commit()

	def cleanup(self):
		if self.stats:
			self.show_stats()
		self.db.commit()
		self.db.close()

	def show_stats(self):
		print "Initial record counts:\n%10s: %d\n%10s: %d" % ("instance", self.instance_recs, "host", self.host_recs)
		print "Last record time: ", dt.fromtimestamp(self.last_instance_tstamp).isoformat(' ')
		print "Records inserted: ", self.insert_count
		print "Records  skipped: ", self.skip_count

	def process_aggregate(self, data, tstamp, host):
		if tstamp <= self.last_host_tstamp:
			self.skip_count += 1
			return
		# the data fields are: host, vcpus, wall time, cpu time, derived efficiency
		(_, vcpus, wall_time, cpu_time, eff) = data.split(',')
	
		if self.verbose:
			print "insert into host_stats values (%d, %s, %d, %d, %f)" % (int(tstamp), host, int(vcpus), int(wall_time), float(cpu_time))
		if not self.dry_run:
			self.cursor.execute("insert into host_stats values (?, ?, ?, ?, ?)", (int(tstamp), host, int(vcpus), int(wall_time), float(cpu_time)))
			self.insert_count += 1

	def process_instance(self, data, tstamp, host):
		if tstamp <= self.last_instance_tstamp:
			self.skip_count += 1
			return
		(uuid, _, vcpus, wall_time, _, cpu_time, _) = data.split(',')

		if self.verbose:
			print "insert into instance_stats values (%d, %s, %s, %d, %d, %f)" % (int(tstamp), uuid, host, int(vcpus), int(wall_time), float(cpu_time))
		if not self.dry_run:
			self.cursor.execute("insert into instance_stats values (?, ?, ?, ?, ?, ?)",  (int(tstamp), uuid, host, int(vcpus), int(wall_time), float(cpu_time)))
			self.insert_count += 1

	def process_log_file(self, log):
		for line in log:
			tstamp = time.mktime(dt.strptime(line[0:15]+" 2015", "%b %d %X %Y").timetuple())
		
			(host, rtype, data) = line[16:].split()
			if rtype == "os_cpu_aggregate:":
				self.process_aggregate(data, tstamp, host)
			elif rtype == "os_cpu_usage:":
				self.process_instance(data, tstamp, host)
			else:
				print "Unknown record type"
	
		db.commit()

if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument("--logfile", nargs=1, help="path to os_stats logfile", default=[logfile])
	parser.add_argument("--dbfile", nargs=1, help="path to SQLite3 database file", default=[dbfile])
	parser.add_argument("-v", "--verbose", action='store_true', help="verbose processing")
	parser.add_argument("-s", "--stats", action='store_true', default=False, help="print processing stats")
	parser.add_argument("--dry-run", action='store_true', default=False, help="make no changes to the database")
	args = parser.parse_args()

	log = open(args.logfile[0], "r")
	db = sqlite3.connect(args.dbfile[0])

	logparser = LogParser(db, args)
	logparser.process_log_file(log)
	logparser.cleanup()
