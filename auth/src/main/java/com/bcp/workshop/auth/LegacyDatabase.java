package com.bcp.workshop.auth;

import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import org.jboss.logging.Logger;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

@ApplicationScoped
public class LegacyDatabase {
    private static final Logger LOGGER = Logger.getLogger(LegacyDatabase.class);
    private static final List<UserSeed> SEED_USERS = List.of(
            new UserSeed("student", "Workshop123!", "Workshop Student", "STUDENT"),
            new UserSeed("trainer", "Trainer123!", "Workshop Trainer", "TRAINER")
    );
    @ConfigProperty(name = "auth.db.url")
    String databaseUrl;

    @Inject
    PasswordHasher passwordHasher;

    @PostConstruct
    void initialize() {
        try {
            Files.createDirectories(Path.of("data"));
            try (Connection connection = DriverManager.getConnection(databaseUrl); Statement statement = connection.createStatement()) {
                statement.executeUpdate("CREATE TABLE IF NOT EXISTS legacy_users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT NOT NULL, display_name TEXT NOT NULL, role TEXT NOT NULL)");
                insertSeedUsers(connection);
                migratePlainTextPasswords(connection);
            }
        } catch (Exception error) {
            LOGGER.error("Database initialization failed", error);
        }
    }

    private void insertSeedUsers(Connection connection) throws SQLException {
        String sql = "INSERT OR IGNORE INTO legacy_users(username, password, display_name, role) VALUES (?, ?, ?, ?)";
        try (PreparedStatement statement = connection.prepareStatement(sql)) {
            for (UserSeed seed : SEED_USERS) {
                statement.setString(1, seed.username());
                statement.setString(2, passwordHasher.hash(seed.password()));
                statement.setString(3, seed.displayName());
                statement.setString(4, seed.role());
                statement.executeUpdate();
            }
        }
    }

    private void migratePlainTextPasswords(Connection connection) throws SQLException {
        List<PasswordEntry> entries = new ArrayList<>();
        try (Statement statement = connection.createStatement();
             ResultSet result = statement.executeQuery("SELECT id, password FROM legacy_users")) {
            while (result.next()) {
                String storedPassword = result.getString("password");
                if (!passwordHasher.isHashed(storedPassword)) {
                    entries.add(new PasswordEntry(result.getLong("id"), storedPassword));
                }
            }
        }

        try (PreparedStatement statement = connection.prepareStatement(
                "UPDATE legacy_users SET password = ? WHERE id = ?")) {
            for (PasswordEntry entry : entries) {
                statement.setString(1, passwordHasher.hash(entry.password()));
                statement.setLong(2, entry.id());
                statement.executeUpdate();
            }
        }
    }

    public UserRecord findByCredentials(String username, String password) {
        String sql = "SELECT id, username, display_name, role, password FROM legacy_users WHERE username = ?";
        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, username);
            try (ResultSet result = statement.executeQuery()) {
                if (result.next()) {
                    if (passwordHasher.verify(password, result.getString("password"))) {
                        return new UserRecord(result.getLong("id"), result.getString("username"), result.getString("display_name"), result.getString("role"));
                    }
                }
            }
        } catch (Exception error) {
            LOGGER.error("Credential lookup failed", error);
        }
        return null;
    }

    private record UserSeed(String username, String password, String displayName, String role) {}

    private record PasswordEntry(long id, String password) {}
}
