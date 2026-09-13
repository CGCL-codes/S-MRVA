
public class TestLog4 {
  private final static Logger log = Logger.getLogger(Logger.GLOBAL_LOGGER_NAME);

  @Override
  public void doFilter(ServletRequest request, ServletResponse response,
    FilterChain chain) throws IOException, ServletException {
      HttpServletRequest httpServletReq = (HttpServletRequest) request;
      // ruleid: crlf-injection-logs
      String param = httpServletReq.getParameter("param");
      log.log(log.getLevel(), param);
  }
}
