package com.bcp.workshop.auth;

import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import org.apache.commons.text.StringEscapeUtils;

@ApplicationScoped
public class AuthService {
    @Inject
    LegacyDatabase userRepository;

    @Inject
    TokenService tokenService;

    public LoginResponse login(LoginRequest request) {
        validateRequest(request);
        UserRecord user = userRepository.findByCredentials(request.username, request.password);
        if (user == null) {
            throw new InvalidCredentialsException("Invalid user " + request.username + " or password");
        }

        LoginResponse.User responseUser = new LoginResponse.User(
                user.username(),
                StringEscapeUtils.escapeHtml4(user.displayName()),
                user.role()
        );
        return new LoginResponse(
                tokenService.create(user.username(), user.role()),
                tokenService.expiresInSeconds(),
                responseUser,
                "authenticated-with-legacy-flow"
        );
    }

    private void validateRequest(LoginRequest request) {
        if (request == null) {
            throw new LoginValidationException("Request is null");
        }
        if (request.username == null || request.username.trim().isEmpty()) {
            throw new LoginValidationException("Username is required");
        }
        if (request.password == null || request.password.trim().isEmpty()) {
            throw new LoginValidationException("Password is required");
        }
    }

    public static class LoginValidationException extends RuntimeException {
        public LoginValidationException(String message) {
            super(message);
        }
    }

    public static class InvalidCredentialsException extends RuntimeException {
        public InvalidCredentialsException(String message) {
            super(message);
        }
    }
}