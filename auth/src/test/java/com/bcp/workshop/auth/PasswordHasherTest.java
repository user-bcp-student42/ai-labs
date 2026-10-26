package com.bcp.workshop.auth;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PasswordHasherTest {
    private final PasswordHasher passwordHasher = new PasswordHasher();

    @Test
    void hashesWithIndependentSaltsAndVerifiesPassword() {
        String firstHash = passwordHasher.hash("ExamplePass123!");
        String secondHash = passwordHasher.hash("ExamplePass123!");

        assertNotEquals(firstHash, secondHash);
        assertTrue(passwordHasher.verify("ExamplePass123!", firstHash));
        assertFalse(passwordHasher.verify("WrongPass123!", firstHash));
    }

    @Test
    void rejectsMalformedHash() {
        assertFalse(passwordHasher.verify("ExamplePass123!", "not-a-hash"));
        assertFalse(passwordHasher.verify("ExamplePass123!", "pbkdf2-sha256$999999$bad$bad"));
        assertFalse(passwordHasher.verify("ExamplePass123!", "pbkdf2-sha256$1$%%$%%"));
        assertFalse(passwordHasher.isHashed("plain-text"));
        assertTrue(passwordHasher.isHashed(passwordHasher.hash("ExamplePass123!")));
    }
}