CREATE TABLE IF NOT EXISTS items (
    item_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    category       TEXT NOT NULL,
    manufacturer   TEXT NOT NULL,
    model          TEXT NOT NULL,
    serial_no      TEXT NOT NULL UNIQUE,
    quantity       INTEGER NOT NULL CHECK (quantity >= 0),
    available      INTEGER NOT NULL CHECK (available >= 0),
    item_condition TEXT NOT NULL,
    location       TEXT NOT NULL,
    date_acquired  TEXT NOT NULL,
    image_file     TEXT
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id          INTEGER NOT NULL REFERENCES items(item_id),
    borrower_id      TEXT NOT NULL,
    borrower_name    TEXT NOT NULL,
    role             TEXT NOT NULL,
    purpose          TEXT NOT NULL,
    borrowed_on      TEXT NOT NULL,
    due_date         TEXT NOT NULL,
    returned_on      TEXT,
    return_condition TEXT
);

CREATE TABLE IF NOT EXISTS waitlist (
    wait_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id       INTEGER NOT NULL REFERENCES items(item_id),
    borrower_id   TEXT NOT NULL,
    borrower_name TEXT NOT NULL,
    role          TEXT NOT NULL,
    requested_on  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('Admin', 'Student', 'Faculty')),
    full_name     TEXT NOT NULL
);