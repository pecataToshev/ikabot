CREATE TABLE locks
(
    lockName     VARCHAR(64) NOT NULL,
    pid          INTEGER     NOT NULL,
    updated_at   TIMESTAMP   NOT NULL,
    PRIMARY KEY (lockName)
);
