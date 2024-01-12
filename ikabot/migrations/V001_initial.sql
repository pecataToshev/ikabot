CREATE TABLE processes
(
    botName        VARCHAR(16) NOT NULL,
    pid            INTEGER     NOT NULL UNIQUE,
    action         VARCHAR(64) NOT NULL,
    status         VARCHAR(16) NOT NULL,
    lastActionTime TIMESTAMP   NOT NULL,
    nextActionTime TIMESTAMP,
    targetCity     VARCHAR(32),
    objective      VARCHAR(128),
    info           VARCHAR(256),
    PRIMARY KEY (botName, pid)
);

CREATE TABLE storage
(
    botName    VARCHAR(16) NOT NULL,
    storageKey VARCHAR(32) NOT NULL,
    data       TEXT,
    PRIMARY KEY (botName, storageKey)
);

