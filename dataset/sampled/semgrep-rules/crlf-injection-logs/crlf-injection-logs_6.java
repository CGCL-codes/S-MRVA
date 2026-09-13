
public class OkTestLog2 {
  @Override
  public void doFilter(ServletRequest request, ServletResponse response,
    FilterChain chain) throws IOException, ServletException {
      Logger log = Logger.getLogger(Logger.GLOBAL_LOGGER_NAME);
      HttpServletRequest httpServletReq = (HttpServletRequest) request;
      // ok: crlf-injection-logs
      String param = "foobar";
      log.log(log.getLevel(), param);
  }
}
