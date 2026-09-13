
public class TestLog3 {
  private final static Logger log = Logger.getLogger(Logger.GLOBAL_LOGGER_NAME);

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
      // ruleid: crlf-injection-logs
      log.info("foo"+request.getParameter("param"));
      response.getWriter().append("Served at: ").append(request.getContextPath());
  }
}
