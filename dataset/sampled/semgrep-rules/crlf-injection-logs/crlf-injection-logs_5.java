
public class OkTestLog1 {
  private final static NotLogger log = new NorLogger();

  @Override
  public void doFilter(ServletRequest request, ServletResponse response,
    FilterChain chain) throws IOException, ServletException {
      HttpServletRequest httpServletReq = (HttpServletRequest) request;
      // ok: crlf-injection-logs
      String param = httpServletReq.getParameter("param");
      log.info(param);
  }
}
