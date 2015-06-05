
create table instances (
	tstamp integer,
	uuid varchar(36),
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float,
	primary key (tstamp, uuid)
);

create index instances_tstamp_index on instances (tstamp);
create index instances_uuid_index on instances (uuid);
create index instances_uuid_tstamp_index on instances (uuid, tstamp);

create table hosts (
	tstamp integer,
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float,
	primary key (tstamp, host)
);

create index hosts_tstamp_inex on instances (tstamp);
create index hosts_host_index on instances (host);
create index hosts_host_tstamp_index on instances (host, tstamp);

