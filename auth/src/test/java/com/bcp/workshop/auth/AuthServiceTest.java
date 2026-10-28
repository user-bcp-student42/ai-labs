package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class AuthServiceTest {
    private static final String TEST_SECRET = "test-only-signing-key-never-used-in-production";

    @Test
    void escapesDisplayNameForHtmlOutput() {
        AuthService service = createService("<b>Ana & \"Lo\"</b>");
        LoginRequest request = new LoginRequest();
        request.username = "student";
        request.password = "student-password";

        LoginResponse response = service.login(request);

        assertEquals("&lt;b&gt;Ana &amp; &quot;Lo&quot;&lt;/b&gt;", response.user().displayName());
    }

    private AuthService createService(String displayName) {
        LegacyDatabase database = new LegacyDatabase() {
            @Override
            public UserRecord findByCredentials(String username, String password) {
                return new UserRecord(1L, username, displayName, "STUDENT");
            }
        };
        TokenService tokenService = new TokenService();
        tokenService.objectMapper = new com.fasterxml.jackson.databind.ObjectMapper();
        tokenService.secret = TEST_SECRET;
        tokenService.issuer = "ai-labs-auth";
        tokenService.timeToLiveSeconds = 3600;

        AuthService service = new AuthService();
        service.userRepository = database;
        service.tokenService = tokenService;
        return service;
    }
}
