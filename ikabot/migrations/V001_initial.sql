CREATE TABLE processes
(
    accountName VARCHAR(16) NOT NULL,
    pid         INTEGER     NOT NULL UNIQUE,
    action      VARCHAR(64) NOT NULL,
    status      VARCHAR(16) NOT NULL,
    lastAction  TIMESTAMP   NOT NULL,
    nextAction  TIMESTAMP,
    targetCity  VARCHAR(32),
    objective   VARCHAR(128),
    info        VARCHAR(256),
    PRIMARY KEY (accountName, pid)
);

CREATE TABLE storage
(
    accountName VARCHAR(16) NOT NULL,
    storageKey  VARCHAR(32) NOT NULL,
    data        TEXT,
    PRIMARY KEY (accountName, storageKey)
);

