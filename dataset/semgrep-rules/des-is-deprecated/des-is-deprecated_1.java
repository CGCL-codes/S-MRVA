
package servlets;

import java.io.File;
import java.io.IOException;
import java.io.PrintWriter;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

public class Cls extends HttpServlet
{
    private static org.apache.log4j.Logger log = Logger.getLogger(Register.class);

    protected void danger2(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        // ruleid: des-is-deprecated
        Cipher c = Cipher.getInstance("DES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, k, iv);
        byte[] cipherText = c.doFinal(plainText);
    }
}
