package com.bcp.workshop.auth;

public record LoginResponse(String token, long expiresIn, User user, String debug) {
    public record User(String username, String displayName, String role) {}
}