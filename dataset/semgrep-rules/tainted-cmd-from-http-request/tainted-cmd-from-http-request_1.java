
@WebServlet(value = "/cmdi-00/BenchmarkTest00007")
public class bad2 extends HttpServlet {

    private static final long serialVersionUID = 1L;

    @Override
    public void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        doPost(request, response);
    }

    @Override
    public void doPost(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        // some code
        response.setContentType("text/html;charset=UTF-8");

        String param = "";
        if (request.getHeader("BenchmarkTest00007") != null) {
            param = request.getHeader("BenchmarkTest00007");
        }

        // URL Decode the header value since req.getHeader() doesn't. Unlike req.getParameter().
        param = java.net.URLDecoder.decode(param, "UTF-8");

        String cmd =
                org.owasp.benchmark.helpers.Utils.getInsecureOSCommandString(
                        this.getClass().getClassLoader());
        String[] args = {cmd};
        String[] argsEnv = {param};

        Runtime r = Runtime.getRuntime();

        try {
            // this is vulnerable, but considered a separate issue
            // ok: tainted-cmd-from-http-request
            Process p = r.exec(args, argsEnv);
            org.owasp.benchmark.helpers.Utils.printOSCommandResults(p, response);
        } catch (IOException e) {
            System.out.println("Problem executing cmdi - TestCase");
            response.getWriter()
                    .println(org.owasp.esapi.ESAPI.encoder().encodeForHTML(e.getMessage()));
            return;
        }
    }
}
