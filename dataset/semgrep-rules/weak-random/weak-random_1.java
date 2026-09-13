
package org.owasp.benchmark.testcode;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet(value = "/weakrand-00/BenchmarkTest00066")
public class BenchmarkTest00066 extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    public void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        response.setContentType("text/html;charset=UTF-8");

        String bar;
        int num = 86;
        if ((7 * 42) - num > 200) bar = "This_should_always_happen";
        else bar = param;

        // ruleid: weak-random
        double value = java.lang.Math.random();

        // ok: weak-random
        double value2 = java.security.SecureRandom();
        String rememberMeKey = Double.toString(value).substring(2); // Trim off the 0. at the front.

        // ... rest of the test case code
    }
}
