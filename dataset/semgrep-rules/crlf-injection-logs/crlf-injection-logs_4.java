
public class TestLog5 {

  @Override
  public void doFilter(ServletRequest request, ServletResponse response,
    FilterChain chain) throws IOException, ServletException {
      Logger  log = Logger.getLogger(Logger.GLOBAL_LOGGER_NAME);
      HttpServletRequest httpServletReq = (HttpServletRequest) request;
      // ruleid: crlf-injection-logs
      String param = httpServletReq.getParameter("foo");
      log.log(log.getLevel(), param+"bar");
  }
}
