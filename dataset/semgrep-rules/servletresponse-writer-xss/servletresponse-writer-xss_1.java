
package servlets;

import java.io.IOException;
import java.io.PrintWriter;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class Cls extends HttpServlet
{
    protected void danger2(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        String input1 = req.getParameter("input1");
        // ruleid:servletresponse-writer-xss
        PrintWriter writer = resp.getWriter();
        writer.write(input1);
    }
}
