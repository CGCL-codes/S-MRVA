
public class TestLog2 {
  private final static Logger log = Logger.getLogger(Logger.GLOBAL_LOGGER_NAME);

  @Override
  public void doFilter(ServletRequest request, ServletResponse response,
    FilterChain chain) throws IOException, ServletException {
      HttpServletResponse httpServletResponse = (HttpServletResponse) response;
      // ruleid: crlf-injection-logs
      String param = request.getParameter("param");
      log.log(log.getLevel(), "foo"+param);
  }
}
