drop table if exists user;
create table user(
	user_id integer primary key autoincrement,
	username text not null,
	pw_hash text not null
);

drop table if exists message;
create table message(
	message_id integer primary key autoincrement,
	author_id integer not null,
	title string not null,
	text string not null
);