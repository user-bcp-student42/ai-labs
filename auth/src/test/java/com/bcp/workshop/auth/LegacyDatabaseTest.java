package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class LegacyDatabaseTest {
    @Test
    void migratesLegacyPasswordOnceAndPreservesLoginVerification() throws Exception {
        Class.forName("org.sqlite.JDBC");
        String username = "legacy-" + UUID.randomUUID();
        String plainPassword = "LegacyPass123!";
        Path databasePath = Path.of("target", "legacy-db-" + UUID.randomUUID() + ".sqlite");
        String databaseUrl = "jdbc:sqlite:" + databasePath.toString().replace('\\', '/');
        PasswordHasher passwordHasher = new PasswordHasher();
        LegacyDatabase database = new LegacyDatabase();
        database.databaseUrl = databaseUrl;
        database.passwordHasher = passwordHasher;
        database.initialize();

        try {
            try (Connection connection = DriverManager.getConnection(databaseUrl);
                 PreparedStatement insert = connection.prepareStatement(
                         "INSERT INTO legacy_users(username, password, display_name, role) VALUES (?, ?, ?, ?)")) {
                insert.setString(1, username);
                insert.setString(2, plainPassword);
                insert.setString(3, "Legacy User");
                insert.setString(4, "STUDENT");
                insert.executeUpdate();
            }

            database.initialize();
            String migratedPassword = readStoredPassword(databaseUrl, username);
            assertNotEquals(plainPassword, migratedPassword);
            assertTrue(passwordHasher.verify(plainPassword, migratedPassword));

            database.initialize();
            assertEquals(migratedPassword, readStoredPassword(databaseUrl, username));
        } finally {
            try (Connection connection = DriverManager.getConnection(databaseUrl);
                 PreparedStatement delete = connection.prepareStatement(
                         "DELETE FROM legacy_users WHERE username = ?")) {
                delete.setString(1, username);
                delete.executeUpdate();
            }
            Files.deleteIfExists(databasePath);
        }
    }

    private String readStoredPassword(String databaseUrl, String username) throws Exception {
        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password FROM legacy_users WHERE username = ?")) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    throw new AssertionError("User was not found after migration");
                }
                return result.getString("password");
            }
        }
    }
}