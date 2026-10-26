package com.bcp.workshop.auth;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.eclipse.microprofile.config.inject.ConfigProperty;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;

@ApplicationScoped
public class TokenService {
    private static final String SIGNATURE_ALGORITHM = "HmacSHA256";
    private static final String JWT_ALGORITHM = "HS256";
    private static final String JWT_TYPE = "JWT";
    private static final int MINIMUM_SECRET_LENGTH_BYTES = 32;

    @Inject
    ObjectMapper objectMapper;

    @ConfigProperty(name = "auth.token.secret")
    String secret;

    @ConfigProperty(name = "auth.token.issuer")
    String issuer;

    @ConfigProperty(name = "auth.token.ttl-seconds")
    long timeToLiveSeconds;

    @PostConstruct
    void validateConfiguration() {
        if (secret == null || secret.getBytes(StandardCharsets.UTF_8).length < MINIMUM_SECRET_LENGTH_BYTES) {
            throw new IllegalStateException("AUTH_TOKEN_SECRET must contain at least 32 bytes");
        }
    }

    public String create(String username, String role) {
        Instant issuedAt = Instant.now();
        String encodedHeader = encodeJson(Map.of("alg", JWT_ALGORITHM, "typ", JWT_TYPE));
        String encodedClaims = encodeJson(Map.of(
                "sub", username,
                "role", role,
                "iss", issuer,
                "iat", issuedAt.getEpochSecond(),
                "exp", issuedAt.plusSeconds(timeToLiveSeconds).getEpochSecond()
        ));
        String content = encodedHeader + "." + encodedClaims;
        return content + "." + Base64.getUrlEncoder().withoutPadding().encodeToString(sign(content));
    }

    public long expiresInSeconds() {
        return timeToLiveSeconds;
    }

    private String encodeJson(Object value) {
        try {
            return Base64.getUrlEncoder().withoutPadding().encodeToString(objectMapper.writeValueAsBytes(value));
        } catch (JsonProcessingException error) {
            throw new IllegalStateException("JWT claims could not be encoded", error);
        }
    }

    private byte[] sign(String content) {
        try {
            Mac mac = Mac.getInstance(SIGNATURE_ALGORITHM);
            mac.init(new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), SIGNATURE_ALGORITHM));
            return mac.doFinal(content.getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            throw new IllegalStateException("JWT signing is unavailable", error);
        }
    }
}