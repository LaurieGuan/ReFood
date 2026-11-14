-- Apply explicitly to the selected database; app startup never runs DDL.
CREATE TABLE IF NOT EXISTS pantry (
    user_id VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin PRIMARY KEY,
    payload LONGTEXT NOT NULL
) ENGINE=InnoDB;
