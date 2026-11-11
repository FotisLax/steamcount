CREATE TABLE games(
	app_id int PRIMARY KEY,
	name text NOT NULL,
	tracked boolean NOT NULL DEFAULT true,
	added_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE player_counts(
	app_id int NOT NULL REFERENCES games(app_id),
	ts timestamptz NOT NULL,
	players int NOT NULL,
	PRIMARY KEY (app_id, ts)
);

CREATE TABLE poll_errors(
	id bigserial PRIMARY KEY,
	app_id int,
	ts timestamptz NOT NULL DEFAULT now(),
	error text
);
