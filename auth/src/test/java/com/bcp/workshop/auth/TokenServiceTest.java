package com.bcp.workshop.auth;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertThrows;

class TokenServiceTest {
    private static final String TEST_SECRET = "test-only-signing-key-never-used-in-production";

    @Test
    void rejectsSigningSecretShorterThanMinimum() {
        TokenService tokenService = createTokenService(new ObjectMapper());
        tokenService.secret = "too-short";

        assertThrows(IllegalStateException.class, tokenService::validateConfiguration);
    }

    @Test
    void reportsJsonEncodingFailure() {
        ObjectMapper failingMapper = new ObjectMapper() {
            @Override
            public byte[] writeValueAsBytes(Object value) throws JsonProcessingException {
                throw new JsonProcessingException("test serialization failure") {};
            }
        };
        TokenService tokenService = createTokenService(failingMapper);

        assertThrows(IllegalStateException.class, () -> tokenService.create("student", "STUDENT"));
    }

    private TokenService createTokenService(ObjectMapper objectMapper) {
        TokenService tokenService = new TokenService();
        tokenService.objectMapper = objectMapper;
        tokenService.secret = TEST_SECRET;
        tokenService.issuer = "ai-labs-auth";
        tokenService.timeToLiveSeconds = 3600;
        return tokenService;
    }
}