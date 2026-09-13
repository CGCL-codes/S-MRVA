
package jwt_test.jwt_test_1;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTCreationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.auth0.jwt.interfaces.JWTVerifier;

abstract class App2
{
    private void bad( String[] args )
    {
        System.out.println( "Hello World!" );

        try {
            Algorithm algorithm = Algorithm.none();

            String token = JWT.create()
                .withIssuer("auth0")
                .sign(algorithm);
            // ruleid: java-jwt-decode-without-verify
            DecodedJWT jwt = JWT.decode(token);

        } catch (JWTCreationException exception){
            //Invalid Signing configuration / Couldn't convert Claims.
        }
    }
}
