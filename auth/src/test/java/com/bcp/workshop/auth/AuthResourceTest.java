package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.quarkus.test.junit.QuarkusMock;
import org.eclipse.microprofile.config.inject.ConfigProperty;
import jakarta.inject.Inject;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.Base64;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.Matchers.empty;
import static org.hamcrest.Matchers.isEmptyOrNullString;
import static org.hamcrest.Matchers.nullValue;
import static org.hamcrest.Matchers.notNullValue;

@QuarkusTest
class AuthResourceTest {
    @ConfigProperty(name = "auth.db.url")
    String databaseUrl;

    @ConfigProperty(name = "auth.token.secret")
    String tokenSecret;

    @Inject
    PasswordHasher passwordHasher;

    @BeforeEach
    void requiresIsolatedTestDatabase() {
        assertTrue(databaseUrl.endsWith("target/auth-tests.db"));
    }

    @Test
    void logsInWithWorkshopUser() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\",\"client\":\"angular-workshop\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .body("user.username", is("student"))
                .body("user.displayName", is("Workshop Student"))
                .body("user.role", is("STUDENT"))
                .body("expiresIn", is(3600))
                .body("debug", is("authenticated-with-legacy-flow"))
                .body("token", notNullValue());
    }

    @Test
    void rejectsInvalidCredentials() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"wrong\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("message", is("Invalid user student or password"));
    }

    @Test
    void rejectsUsernameContainingQuote() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"student'\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(401)
                .body("message", is("Invalid user student' or password"));
    }

    @Test
    void authenticatesStoredUsernameContainingQuote() throws Exception {
        String username = "o'connor";
        String password = "QuotedUser123!";
        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement insert = connection.prepareStatement(
                     "INSERT OR REPLACE INTO legacy_users(username, password, display_name, role) VALUES (?, ?, ?, ?)")) {
            insert.setString(1, username);
            insert.setString(2, passwordHasher.hash(password));
            insert.setString(3, "Quoted User");
            insert.setString(4, "STUDENT");
            insert.executeUpdate();
        }

        try {
            given()
                    .contentType("application/json")
                    .body("{\"username\":\"o'connor\",\"password\":\"QuotedUser123!\"}")
                    .when().post("/auth/login")
                    .then()
                    .statusCode(200)
                    .body("user.username", is(username));
        } finally {
            try (Connection connection = DriverManager.getConnection(databaseUrl);
                 PreparedStatement delete = connection.prepareStatement(
                         "DELETE FROM legacy_users WHERE username = ?")) {
                delete.setString(1, username);
                delete.executeUpdate();
            }
        }
    }

    @Test
    void requiresUsernameAndPassword() {
        given()
                .contentType("application/json")
                .body("{\"username\":\"\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Username is required"));

        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Password is required"));

            given()
                .contentType("application/json")
                .body("{\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Username is required"));

            given()
                .contentType("application/json")
                .body("{\"username\":\"student\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Password is required"));
    }

            @Test
            void rejectsWhitespaceOnlyCredentials() {
            given()
                .contentType("application/json")
                .body("{\"username\":\"   \",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Username is required"));

            given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"   \"}")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Password is required"));
            }

    @Test
    void rejectsNullRequestBody() {
        given()
                .contentType("application/json")
                .body("null")
                .when().post("/auth/login")
                .then()
                .statusCode(400)
                .body("message", is("Request is null"));
    }

    @Test
    void storesSeedPasswordAsSaltedHash() throws Exception {
        given()
            .contentType("application/json")
            .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
            .when().post("/auth/login")
            .then()
            .statusCode(200);

        try (Connection connection = DriverManager.getConnection(databaseUrl);
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT password FROM legacy_users WHERE username = ?")) {
            statement.setString(1, "student");
            try (ResultSet result = statement.executeQuery()) {
                    assertTrue(result.next());
                    String storedPassword = result.getString("password");
                    assertFalse("Workshop123!".equals(storedPassword));
                    assertTrue(storedPassword.startsWith("pbkdf2-sha256$"));
            }
        }
    }

    @Test
    void tokenIsSignedJwtWithExplicitClaims() throws Exception {
        String token = given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .extract().path("token");

        String[] tokenParts = token.split("\\.");
        assertEquals(3, tokenParts.length);

        String header = new String(Base64.getUrlDecoder().decode(tokenParts[0]), StandardCharsets.UTF_8);
        String claims = new String(Base64.getUrlDecoder().decode(tokenParts[1]), StandardCharsets.UTF_8);
        com.fasterxml.jackson.databind.ObjectMapper mapper = new com.fasterxml.jackson.databind.ObjectMapper();
        com.fasterxml.jackson.databind.JsonNode headerJson = mapper.readTree(header);
        com.fasterxml.jackson.databind.JsonNode claimsJson = mapper.readTree(claims);
        assertEquals("HS256", headerJson.path("alg").asText());
        assertEquals("JWT", headerJson.path("typ").asText());
        assertEquals("student", claimsJson.path("sub").asText());
        assertEquals("STUDENT", claimsJson.path("role").asText());
        assertEquals("ai-labs-auth", claimsJson.path("iss").asText());
        assertTrue(claimsJson.path("exp").asLong() > System.currentTimeMillis() / 1000);
        assertFalse(claims.contains(tokenSecret));
        assertTrue(hasValidSignature(token, tokenSecret));

        String changedPayload = tokenParts[0] + "." + tokenParts[1] + "x." + tokenParts[2];
        assertFalse(hasValidSignature(changedPayload, tokenSecret));
    }

    private boolean hasValidSignature(String token, String secret) throws Exception {
        String[] tokenParts = token.split("\\.");
        if (tokenParts.length != 3) {
            return false;
        }
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        byte[] expectedSignature = mac.doFinal((tokenParts[0] + "." + tokenParts[1]).getBytes(StandardCharsets.UTF_8));
        byte[] actualSignature = Base64.getUrlDecoder().decode(tokenParts[2]);
        return java.security.MessageDigest.isEqual(expectedSignature, actualSignature);
    }

    @Test
    void doesNotAllowUnconfiguredCorsOrigin() {
        given()
                .contentType("application/json")
                .header("Origin", "https://unapproved.example")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(403)
                .body(isEmptyOrNullString())
                .header("Access-Control-Allow-Origin", nullValue());
    }

    @Test
    void allowsConfiguredCorsOrigin() {
        given()
                .contentType("application/json")
                .header("Origin", "http://localhost:4200")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(200)
                .header("Access-Control-Allow-Origin", is("http://localhost:4200"));
    }

    @Test
    void hidesExceptionDetailsFromErrorResponse() {
        QuarkusMock.installMockForType(new AuthService() {
            @Override
            public LoginResponse login(LoginRequest request) {
                throw new IllegalStateException("database-private-detail");
            }
        }, AuthService.class);

        given()
                .contentType("application/json")
                .body("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .when().post("/auth/login")
                .then()
                .statusCode(500)
                .body("message", is("Authentication failed"))
                .body("exception", is("InternalError"));
    }

    @Test
    void healthEndpointReportsServiceUp() {
        given()
                .when().get("/q/health")
                .then()
                .statusCode(200)
                .body("status", is("UP"));
    }

    @Test
    void healthEndpointReportsNoChecksWhenNoneAreRegistered() {
        given()
                .when().get("/q/health")
                .then()
                .statusCode(200)
                .body("checks", empty());
    }
}
