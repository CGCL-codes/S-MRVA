
@WebServlet(value = "/trustbound-00/BenchmarkTest00004")
public class BenchmarkTest00004 extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    public void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        response.setContentType("text/html;charset=UTF-8");

        javax.servlet.http.Cookie[] theCookies = request.getCookies();

        String param = "noCookieValueSupplied";
        if (theCookies != null) {
            for (javax.servlet.http.Cookie theCookie : theCookies) {
                if (theCookie.getName().equals("BenchmarkTest00004")) {
                    param = java.net.URLDecoder.decode(theCookie.getValue(), "UTF-8");
                    break;
                }
            }
        }

        // ruleid: tainted-session-from-http-request
        request.getSession().setAttribute("param", param);
    }
}
