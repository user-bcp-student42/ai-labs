package com.bcp.workshop.auth;

import jakarta.inject.Inject;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import jakarta.ws.rs.core.Response;
import org.jboss.logging.Logger;

import java.util.Map;

@Path("/auth")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class AuthResource {
    private static final Logger LOGGER = Logger.getLogger(AuthResource.class);

    @Inject
    AuthService authService;

    @POST
    @Path("/login")
    public Response login(LoginRequest request) {
        try {
            return Response.ok(authService.login(request)).build();
        } catch (AuthService.LoginValidationException error) {
            return Response.status(400).entity(Map.of("message", error.getMessage())).build();
        } catch (AuthService.InvalidCredentialsException error) {
            return Response.status(401).entity(Map.of("message", error.getMessage())).build();
        } catch (Exception error) {
            LOGGER.error("Authentication request failed", error);
            return Response.status(500).entity(Map.of(
                "message", "Authentication failed",
                "exception", "InternalError"
            )).build();
        }
    }
}
