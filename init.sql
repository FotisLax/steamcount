CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS games (
    app_id       integer PRIMARY KEY,
    name         text NOT NULL,
    tracked      boolean NOT NULL DEFAULT true,
    added_at     timestamptz NOT NULL DEFAULT now(),
    last_polled  timestamptz,
    poll_every   interval NOT NULL DEFAULT '1 day'
);

CREATE INDEX IF NOT EXISTS games_name_trgm
    ON games USING gin (name gin_trgm_ops);

CREATE TABLE IF NOT EXISTS player_counts (
    app_id   integer NOT NULL REFERENCES games(app_id),
    ts       timestamptz NOT NULL,
    players  integer NOT NULL,
    PRIMARY KEY (app_id, ts)
);

CREATE TABLE IF NOT EXISTS poll_errors (
    id      bigserial PRIMARY KEY,
    app_id  integer,
    ts      timestamptz NOT NULL DEFAULT now(),
    error   text
);

INSERT INTO games (app_id, name, poll_every) VALUES
 (730,'Counter-Strike 2','5 minutes'), (570,'Dota 2','5 minutes'),
 (578080,'PUBG','5 minutes'), (1172470,'Apex Legends','5 minutes'),
 (1245620,'Elden Ring','5 minutes'), (1086940,'Baldur''s Gate 3','5 minutes'),
 (553850,'Helldivers 2','5 minutes'), (1623730,'Palworld','5 minutes'),
 (1091500,'Cyberpunk 2077','5 minutes'), (252490,'Rust','5 minutes'),
 (105600,'Terraria','5 minutes'), (413150,'Stardew Valley','5 minutes'),
 (271590,'GTA V','5 minutes'), (440,'Team Fortress 2','5 minutes'),
 (238960,'Path of Exile','5 minutes'), (1085660,'Destiny 2','5 minutes'),
 (1966720,'Lethal Company','5 minutes')
ON CONFLICT DO NOTHING;