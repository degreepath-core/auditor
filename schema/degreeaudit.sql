create database degreeaudit;

create table if not exists result
(
	id serial not null
		constraint result_pkey
			primary key,
	student_id text not null,
	duration interval default '00:00:00'::interval not null,
	iterations integer default 0 not null,
	per_iteration interval default '00:00:00'::interval not null,
	rank numeric default 0 not null,
	result jsonb,
	claimed_courses jsonb default '{}'::jsonb not null,
	ok boolean default false not null,
	ts timestamp with time zone default now() not null,
	gpa numeric default 0.00,
	error jsonb,
	in_progress boolean default false not null,
	area_code text,
	catalog text,
	run integer not null,
	max_rank numeric default 1,
	potential_clbids jsonb default '{}'::jsonb not null,
	input_data jsonb,
	status text default 'unknown'::text not null,
	expires_at timestamp with time zone,
	link_only boolean default false not null,
	revision integer default 0 not null,
	result_version integer default 2 not null,
	is_active boolean default false not null,
	student_classification text,
	student_class integer,
	student_name text,
	student_name_sort text
);

create index if not exists result_area_code_index
	on result (area_code);

create index if not exists result_student_id_area_code_index
	on result (student_id, area_code);

create index if not exists result_status_index
	on result (status);

create index if not exists result_resulttext_hash
	on result (hashtext(result::text));

create index if not exists result_is_active_nulls_idx
	on result (is_active)
	where (is_active IS NULL);

create index if not exists result_revision_nulls_idx
	on result (revision)
	where (revision IS NULL);

create unique index if not exists result_is_active_student_id_area_code_idx
	on result (is_active, student_id, area_code)
	where (is_active = true);

create index if not exists result_result_length_idx
	on result (length(result::text))
	where (result IS NOT NULL);

create index if not exists result_classification_index
	on result (student_classification);

create index if not exists result_class_index
	on result (student_class);

create index if not exists result_name_index
	on result (student_name)
	where (student_name IS NOT NULL);

create index if not exists result_run_brin_index
	on result using brin (run);

create index if not exists result_expires_at_index
	on result (expires_at)
	where (expires_at IS NOT NULL);

create index if not exists result_length_idx
	on result (length(result::text));

create index if not exists result_ts_idx
	on result (ts);

create table if not exists exception
(
	student_id text not null,
	area_code text not null,
	path jsonb not null,
	type text not null,
	clbid text,
	forced_pass boolean,
	author text not null,
	ts timestamp with time zone default now() not null,
	notes text default ''::text not null
		constraint notes_chk
			check (char_length(notes) <= 2048),
	exception_id serial not null
		constraint exception_pk
			primary key,
	expected_value numeric,
	override_credits numeric,
	override_subject text,
	updated_at timestamp with time zone default now() not null,
	is_enabled boolean default true
);

create index if not exists exception_area_code_index
	on exception (area_code);

create index if not exists exception_student_id_index
	on exception (student_id);

create table if not exists area
(
	mecpdg text,
	mecptp text,
	mecpcd text not null
		constraint area_pk
			primary key,
	mecpnm text
);

create table if not exists attribute
(
	attr text not null
		constraint attribute_pk
			primary key,
	label text default ''::text not null,
	description text default ''::text not null
);

create table if not exists map_attribute_area
(
	attr text not null
		constraint map_attribute_area_attribute_attr_fk
			references attribute
				on update cascade on delete cascade,
	area_code text not null,
	catalog_year text
);

create unique index if not exists map_attribute_area_attr_area_code_catalog_year_uindex
	on map_attribute_area (attr, area_code, catalog_year);

create table if not exists map_attribute_course
(
	attr text not null
		constraint map_attribute_course_attribute_attr_fk
			references attribute
				on update cascade on delete cascade,
	course text not null,
	ts timestamp with time zone default now() not null,
	added_by text default CURRENT_USER not null
);

create unique index if not exists map_attribute_course_attr_id_course_uindex
	on map_attribute_course (attr, course);

create table if not exists potential_clbids
(
	result_id integer not null
		constraint potential_clbids_result_id_fk
			references result
				on update cascade on delete cascade,
	clause_hash bigint not null,
	clbids text[] default '{}'::text[] not null
);

create unique index if not exists potential_clbids_result_id_clause_hash_uindex
	on potential_clbids (result_id, clause_hash);

create table if not exists notes
(
	student_id text not null,
	area_code text,
	catalog text,
	note text default ''::text not null,
	ts timestamp with time zone default now() not null,
	author text not null,
	id serial not null
		constraint notes_pk
			primary key,
	read_at timestamp with time zone
);

create index if not exists notes_student_id_area_code_catalog_index
	on notes (student_id, area_code, catalog);

create table if not exists template
(
	student_id text not null,
	key text not null,
	id serial not null
		constraint template_pk
			primary key,
	revision integer default 0 not null
);

create index if not exists templates_key_index
	on template (key);

create index if not exists templates_student_id_index
	on template (student_id);

create index if not exists templates_student_rev_key_uindex
	on template (student_id, key, revision);

create unique index if not exists template_student_id_key_uindex
	on template (student_id, key);

create table if not exists map_template_course
(
	template_id integer not null
		constraint map_template_course_template_id_fk
			references template
				on update cascade on delete cascade,
	course text not null
);

create unique index if not exists map_template_course_uindex
	on map_template_course (template_id, course);

create table if not exists audit.attributes
(
	id serial not null
		constraint attributes_pkey
			primary key,
	tstamp timestamp with time zone default now(),
	schema_name text,
	table_name text,
	operation text,
	who text default CURRENT_USER,
	new_val jsonb,
	old_val jsonb
);

create table if not exists map_constant_area
(
	area_code text not null,
	course text not null,
	crsid text,
	lineid integer generated always as identity
);

create unique index if not exists map_constant_area_area_code_course_crsid_idx
	on map_constant_area (area_code, course, crsid);

create table if not exists queue
(
	id bigint generated by default as identity
		constraint queue_pkey
			primary key,
	ts timestamp with time zone default now() not null,
	priority integer default 100 not null,
	student_id text not null,
	area_catalog text not null,
	area_code text not null,
	input_data jsonb not null,
	run integer,
	expires_at timestamp with time zone,
	link_only boolean default false not null
);

create table if not exists analytics
(
	id bigint generated always as identity,
	ts timestamp with time zone default now() not null,
	ip inet not null,
	is_student boolean not null,
	is_faculty boolean not null,
	is_staff boolean not null,
	is_parent boolean not null,
	is_chair boolean not null,
	is_assoc_dean boolean not null,
	is_registrar boolean not null,
	is_superuser boolean not null,
	spoofer_ppnum text,
	spoofer_login text,
	ppnum text not null,
	login text not null,
	action text not null,
	result_id bigint,
	area_catalog text,
	area_code text,
	stnum text
);

comment on column analytics.ip is 'Logged in User IP Address';

comment on column analytics.spoofer_ppnum is 'People Number of the person spoofing';

comment on column analytics.ppnum is 'People Number';

create index if not exists analytics_ts_idx
	on analytics (ts);

create table if not exists audit.exception
(
	id serial not null
		constraint exception_pkey
			primary key,
	tstamp timestamp with time zone default now(),
	schema_name text,
	table_name text,
	operation text,
	who text default CURRENT_USER,
	new_val jsonb,
	old_val jsonb
);

create table if not exists audit.notes
(
	id serial not null
		constraint notes_pkey
			primary key,
	tstamp timestamp with time zone default now(),
	schema_name text,
	table_name text,
	operation text,
	who text default CURRENT_USER,
	new_val jsonb,
	old_val jsonb
);

create table if not exists what_if_catalog_change
(
	student_id text not null,
	area_code text not null,
	old_catalog text not null,
	new_catalog text not null,
	is_active boolean default true not null,
	who text not null,
	ts timestamp with time zone default now() not null,
	note text default ''::text not null,
	constraint what_if_catalog_pk
		unique (student_id, area_code)
);

create table if not exists what_if_add
(
	student_id text not null,
	area_code text not null,
	who text not null,
	ts timestamp with time zone default now() not null,
	note text default ''::text not null,
	constraint what_if_add_pk
		unique (student_id, area_code)
);

create table if not exists student.contract_majors
(
	student_id text not null,
	area_code text not null,
	who text,
	ts timestamp with time zone default now() not null,
	constraint contract_majors_pk
		primary key (student_id, area_code)
);

create index if not exists contract_majors_student_id_index
	on student.contract_majors (student_id);

create table if not exists what_if_drop
(
	student_id text not null,
	area_code text not null,
	who text not null,
	ts timestamp with time zone default now() not null,
	note text default ''::text not null,
	constraint what_if_drop_pk
		unique (student_id, area_code)
);

create table if not exists student.change_area_catalog
(
	student_id text not null,
	area_code text not null,
	catalog text not null,
	is_active boolean not null,
	added_by text not null,
	added_at timestamp with time zone not null,
	note text default ''::text not null,
	lineid integer generated always as identity
		constraint change_area_catalog_pk
			primary key,
	changed_by text not null,
	changed_at timestamp with time zone not null
);

create index if not exists change_area_catalog_student_id_area_code_index
	on student.change_area_catalog (student_id, area_code);

create unique index if not exists change_area_catalog_student_id_area_code_idx
	on student.change_area_catalog (student_id, area_code)
	where (is_active = true);

create table if not exists queue_block
(
	student_id text not null,
	area_code text not null,
	added_at timestamp with time zone not null,
	added_by text not null,
	constraint queue_block_pk
		primary key (student_id, area_code)
);

create table if not exists report_type
(
	name text not null
		constraint report_type_pkey
			primary key,
	description text not null
);

create table if not exists report
(
	report_type text not null
		constraint report_report_type_fkey
			references report_type
				on update cascade,
	area_code text not null,
	content text not null,
	last_changed_at timestamp with time zone not null,
	constraint report_pkey
		primary key (area_code, report_type)
);

create table if not exists queue_reports
(
	id bigint generated by default as identity
		constraint queue_reports_pkey
			primary key,
	ts timestamp with time zone default now() not null,
	area_code text not null,
	filter_by_class_year text,
	filter_by_classification text,
	filter_by_catalog_year text
);
