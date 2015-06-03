
drop table instance_stats;
create table instance_stats (
	tstamp integer,
	uuid varchar(64),
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float
);

create index tstamp_index on instance_stats (tstamp);
create index uuid_index on instance_stats(uuid);
create index uuid_tstamp_index on instance_stats(uuid, tstamp);

drop table host_stats;
create table host_stats (
	tstamp integer,
	host varchar(64),
	vcpus integer,
	wall_time integer,
	cpu_time float
);
