drop database if exists stats;
create database stats;
use stats;

drop table if exists stats.instances;
create table stats.instances (
	tstamp integer,
	uuid varchar(36),
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float,
	primary key (tstamp, uuid),
	key instances_tstamp_index (tstamp),
	key instances_uuid_index (uuid),
	key instances_uuid_tstamp_index (uuid, tstamp),
	foreign key (uuid) references nova.instances (uuid)
) engine=InnoDB default charset=utf8;

drop table if exists stats.hosts;
create table stats.hosts (
	tstamp integer,
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float,
	primary key (tstamp, host),
	key hosts_tstamp_index (tstamp),
	key hosts_host_index (host),
	key hosts_host_tstamp_index (host, tstamp)
) engine=InnoDB default charset=utf8;

