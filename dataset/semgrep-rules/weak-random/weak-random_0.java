
package org.owasp.benchmark.testcode;

import java.io.IOException;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@WebServlet(value = "/weakrand-00/BenchmarkTest00023")
public class BenchmarkTest00023 extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    public void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        response.setContentType("text/html;charset=UTF-8");

        String param = request.getParameter("BenchmarkTest00023");
        if (param == null) param = "";

        // ruleid: weak-random
        float rand = new java.util.Random().nextFloat();

        // ruleid: weak-random
        new java.util.Random().nextInt();
        String rememberMeKey = Float.toString(rand).substring(2); // Trim off the 0. at the front.

        // ... rest of the test case code
    }
}
