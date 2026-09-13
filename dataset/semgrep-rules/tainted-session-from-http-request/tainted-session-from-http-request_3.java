
@WebServlet(value = "/trustbound-00/BenchmarkTest00321")
public class BenchmarkTest00321 extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    public void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        response.setContentType("text/html;charset=UTF-8");

        String param = "";
        java.util.Enumeration<String> headers = request.getHeaders("BenchmarkTest00321");

        if (headers != null && headers.hasMoreElements()) {
            param = headers.nextElement(); // just grab first element
        }

        // URL Decode the header value since req.getHeaders() doesn't. Unlike req.getParameters().
        param = java.net.URLDecoder.decode(param, "UTF-8");

        String bar = org.owasp.esapi.ESAPI.encoder().encodeForHTML(param);

        // ruleid: tainted-session-from-http-request
        request.getSession().putValue(bar, bar);
    }
}
