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
import gzip
import pprint
from datetime import datetime as dt
import time
import argparse
import ConfigParser
import mysql.connector
from mysql.connector import errorcode

# defaults
logfile="/var/log/os_stats.log"
dbfile="/root/reporting/os_stats/test_stats.sqlite3"
dbhost="localhost"
dbname="stats"

conffile = "/etc/os_stats.conf"

class LogParser:
	def __init__(self, db, args):
		self.db = db
		self.verbose = args['verbose']
		self.dry_run = args['dry_run']
		self.force = args['force']
		self.stats = args['stats']
		self.last_host_tstamp = 0.0
		self.last_instance_tstamp = 0.0

		self.cursor = db.cursor()
		self.cursor.execute("select max(tstamp) from instances")
		tstamp = self.cursor.fetchone()[0]
		if tstamp:
			self.last_host_tstamp = float(tstamp)
		self.cursor.execute("select max(tstamp) from hosts")
		tstamp = self.cursor.fetchone()[0]
		if tstamp:
			self.last_instance_tstamp = float(tstamp)
		self.cursor.execute("select count(*) from instances")
		self.instance_recs = int(self.cursor.fetchone()[0])
		self.cursor.execute("select count(*) from hosts")
		self.host_recs = int(self.cursor.fetchone()[0])

		self.insert_count = 0
		self.skip_count = 0
		self.duplicate_count = 0
		self.error_count = 0

		self.queries_mysql = {
			"instances": "insert into instances values (%s, %s, %s, %s, %s, %s)",
			"hosts": "insert into hosts values (%s, %s, %s, %s, %s)",
		}
		self.queries_sqlite = {
			"instances": "insert into instances values (?, ?, ?, ?, ?, ?)",
			"hosts": "insert into hosts values (?, ?, ?, ?, ?)",
		}

		if isinstance(self.db, sqlite3.Connection):
			self.queries = self.queries_sqlite
			self.execute_query = self.execute_query_sqlite
		else:
			self.queries = self.queries_mysql
			self.execute_query = self.execute_query_mysql

	def commit(self):
		self.db.commit()

	def cleanup(self):
		if self.stats:
			self.show_stats()
		self.db.commit()
		self.db.close()

	def show_stats(self):
		if self.dry_run:
			print "***DRY RUN***"
		print "Initial record counts:\n%10s: %d\n%10s: %d" % ("instance", self.instance_recs, "host", self.host_recs)
		print "Last record time: ", dt.fromtimestamp(self.last_instance_tstamp).isoformat(' ')
		print "Records inserted: ", self.insert_count
		print "Records  skipped: ", self.skip_count
		print "Duplicate records: ", self.duplicate_count
		print "Database  errors: ", self.error_count

	def execute_query_mysql(self, query, args):
		try:
			self.cursor.execute(self.queries[query], args)
			self.insert_count += 1
		except mysql.connector.IntegrityError as err:
			# this captures /both/ the case of a duplicate key and the foreign key reference
			# error. We need to check the errno to figure out which is which
			if err.errno == errorcode.ER_NO_REFERENCED_ROW:
				if self.verbose:
					print "Referential integrity error! %s query failed: %s " % (query, err)
				self.error_count += 1
			else:
				if self.verbose:
					print "Other error! %s query failed: %d %s" % (query, err.errno, err)
				self.duplicate_count += 1

	def execute_query_sqlite(self, query, args):
		try:
			self.cursor.execute(self.queries[query], args)
			self.insert_count += 1
		except sqlite3.IntegrityError as err:
			if self.verbose:
				print "Other error! %s query failed: %s" % (query, pprint.pformat(err))
			self.duplicate_count += 1

	def process_aggregate(self, data, tstamp, host):
		if not self.force and tstamp <= self.last_host_tstamp:
			self.skip_count += 1
			return
		# the data fields are: host, vcpus, wall time, cpu time, derived efficiency
		(_, vcpus, wall_time, cpu_time, eff) = data.split(',')
	
		if self.verbose:
			print "insert into hosts values (%d, %s, %d, %d, %f)" % (int(tstamp), host, int(vcpus), int(wall_time), float(cpu_time))
		if not self.dry_run:
			self.execute_query("hosts", (int(tstamp), host, int(vcpus), int(wall_time), float(cpu_time)))

	def process_instance(self, data, tstamp, host):
		if not self.force and tstamp <= self.last_instance_tstamp:
			self.skip_count += 1
			return
		(uuid, _, vcpus, wall_time, _, cpu_time, _) = data.split(',')

		if self.verbose:
			print "insert into instances values (%d, %s, %s, %d, %d, %f)" % (int(tstamp), uuid, host, int(vcpus), int(wall_time), float(cpu_time))
		if not self.dry_run:
			self.execute_query("instances",  (int(tstamp), uuid, host, int(vcpus), int(wall_time), float(cpu_time)))

	def process_log_file(self, log):
		count=0
		for line in log:
			tstamp = time.mktime(dt.strptime(line[0:15]+" 2015", "%b %d %X %Y").timetuple())
		
			(host, rtype, data) = line[16:].split()
			if rtype == "os_cpu_aggregate:":
				self.process_aggregate(data, tstamp, host)
			elif rtype == "os_cpu_usage:":
				self.process_instance(data, tstamp, host)
			else:
				print "Unknown record type"

			count += 1
			if count > 100:
				self.db.commit()
				count = 0
	
		self.db.commit()

if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	mysql_group = parser.add_argument_group("MySQL DB connection")
	sqlite_group = parser.add_argument_group("SQLite3 DB connection")
	parser.add_argument("--config", help="configuration file", default=conffile)
	parser.add_argument("--logfile", nargs=1, help="path to os_stats logfile", default=[logfile])
	parser.add_argument("-v", "--verbose", action='store_true', help="verbose processing")
	parser.add_argument("-s", "--stats", action='store_true', default=False, help="print processing stats")
	parser.add_argument("--dry-run", action='store_true', default=False, help="make no changes to the database")
	parser.add_argument("--force", action='store_true', default=False, help="try to insert all records and let the database primary keys handle duplication")
	sqlite_group.add_argument("--dbfile", nargs=1, help="path to SQLite3 database file", default=[dbfile])
	mysql_group.add_argument("--dbname", help="MySQL database to use")
	mysql_group.add_argument("--dbhost", help="MySQL server to connect to")
	mysql_group.add_argument("--dbcred", help="MySQL user credentials to connect with. Takes the form user:password[@host[:db]]")
	args = parser.parse_args()

	config = ConfigParser.ConfigParser()
	config_options = {
		'force': False,
		'verbose': False,
		'dry_run': False,
		'stats': True
	}
	try:
		cf = open(conffile, "r")
		config.readfp(cf)
		# walk the configuration options
		#
		# the config file consists of a default section, and an optional mysql section.
		# The contents match the command line arguments, and are overridden by the command
		# line
	
		for section in config.sections():
			config_options[section] = True
			opts = config.items(section)
			for (key, value) in opts:
				config_options[key] = value

	except IOError:
		print "Config file %s not found" % (conffile)
		config_options = {}

	# pull in the command line arguments
	for (key, value) in vars(args).items():
		if value:
			config_options[key] = value

	lfile = config_options['logfile'][0]
	if lfile[-3:] == '.gz':
		log = gzip.open(lfile)
	else:
		log = open(config_options['logfile'][0], "r")

	if 'mysql' in config_options or 'dbcred' in config_options:
		# no default username or password - we fail if they're not supplied
		uname = ""
		passwd = ""
		host = "localhost"
		dbname = "stats"
		# these are used in the config file - there's no way to specify the
		# user and password separately on the command line
		if 'dbuser' in config_options:
			uname = config_options['dbuser']
		if 'dbpasswd' in config_options:
			passwd = config_options['dbpasswd']
		if 'dbhost' in config_options:
			host = config_options['dbhost']
		if 'dbname' in config_options:
			dbname = config_options['dbname']
		if 'dbcred' in config_options:
			print config_options['dbcred']
			upart = config_options['dbcred']
			if '@' in config_options['dbcred']:
				(upart, hpart) = config_options['dbcred'].split('@')
				host = hpart
				if ':' in hpart:
					(host, dbname) = hpart.split(':')

			# note that we specifically use a maxsplit value of 1 here, since
			# the password may contain a ':' (even though it probably
			# shouldn't, given it's the standard separator in passwd files)
			(uname, passwd) = upart.split(':', 1)
		mysql_config = {
			'user': uname,
			'password': passwd,
			'host': host,
			'database': dbname,
		}

		db = mysql.connector.connect(**mysql_config)
	else:
		db = sqlite3.connect(config_options['dbfile'][0])

	logparser = LogParser(db, config_options)
	logparser.process_log_file(log)
	logparser.cleanup()
