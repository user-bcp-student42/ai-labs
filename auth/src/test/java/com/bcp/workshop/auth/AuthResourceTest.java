package com.bcp.workshop.auth;

import io.quarkus.test.junit.QuarkusTest;
import io.restassured.response.ValidatableResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static io.restassured.RestAssured.given;
import static org.hamcrest.CoreMatchers.is;
import static org.hamcrest.CoreMatchers.nullValue;
import static org.hamcrest.Matchers.notNullValue;

@QuarkusTest
class AuthResourceTest {
    private ValidatableResponse login(String body) {
        return given()
                .contentType("application/json")
                .body(body)
                .when().post("/auth/login")
                .then();
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
                .body("token", notNullValue());
    }

    @Test
    @DisplayName("Credenciales válidas: el 200 incluye expiresIn y el perfil completo de student")
    void validLoginReturnsExpiresInAndStudentProfile() {
        login("{\"username\":\"student\",\"password\":\"Workshop123!\"}")
                .statusCode(200)
                .body("token", notNullValue())
                .body("expiresIn", is(3600))
                .body("user.username", is("student"))
                .body("user.displayName", is("Workshop Student"))
                .body("user.role", is("STUDENT"));
    }

    @Test
    @DisplayName("Credenciales válidas: se resuelve el usuario correcto (trainer con su propio rol)")
    void validLoginResolvesTrainerWithOwnRole() {
        login("{\"username\":\"trainer\",\"password\":\"Trainer123!\"}")
                .statusCode(200)
                .body("token", notNullValue())
                .body("user.username", is("trainer"))
                .body("user.role", is("TRAINER"));
    }

    @Test
    @DisplayName("Credenciales inválidas: contraseña incorrecta responde 401 con message y sin token")
    void wrongPasswordReturns401WithoutToken() {
        login("{\"username\":\"student\",\"password\":\"not-the-password\"}")
                .statusCode(401)
                .body("message", is("Invalid user student or password"))
                .body("token", nullValue());
    }

    @Test
    @DisplayName("Credenciales inválidas: usuario inexistente responde 401 sin token")
    void unknownUserReturns401WithoutToken() {
        login("{\"username\":\"nobody\",\"password\":\"whatever\"}")
                .statusCode(401)
                .body("token", nullValue());
    }

    @Test
    @DisplayName("Validación de campos: username ausente responde 400 con message")
    void missingUsernameReturns400() {
        login("{\"password\":\"Workshop123!\"}")
                .statusCode(400)
                .body("message", notNullValue());
    }

    @Test
    @DisplayName("Validación de campos: username en blanco responde 400 con message")
    void blankUsernameReturns400() {
        login("{\"username\":\"   \",\"password\":\"Workshop123!\"}")
                .statusCode(400)
                .body("message", notNullValue());
    }

    @Test
    @DisplayName("Validación de campos: password ausente responde 400 con message")
    void missingPasswordReturns400() {
        login("{\"username\":\"student\"}")
                .statusCode(400)
                .body("message", notNullValue());
    }

    @Test
    @DisplayName("Validación de campos: password en blanco responde 400 con message")
    void blankPasswordReturns400() {
        login("{\"username\":\"student\",\"password\":\"   \"}")
                .statusCode(400)
                .body("message", notNullValue());
    }

    @Test
    @DisplayName("Comillas en un valor no malicioso: o'brien responde 401 (no 500) y sin token")
    void usernameWithSingleQuoteReturns401NotServerError() {
        login("{\"username\":\"o'brien\",\"password\":\"whatever\"}")
                .statusCode(401)
                .body("token", nullValue());
    }
}
