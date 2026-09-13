
package testcode.cookie;

import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

public class UrlRewriting extends HttpServlet {

    // ruleid: url-rewriting
    private String encodeURLRewrite(HttpServletResponse resp, String url) {
        return resp.encodeURL(url);
    }
}
