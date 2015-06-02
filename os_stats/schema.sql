
create table instance_stats (
	tstamp integer,
	uuid varchar(64),
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float
);

create table host_stats (
	tstamp integer,
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float
);
