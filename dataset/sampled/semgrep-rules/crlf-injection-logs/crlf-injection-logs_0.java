
package com.vogella.logger.test;

import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

import com.vogella.logger.MyLogger;

public class TestLog1 {
  private final static Logger log = Logger.getLogger(Logger.GLOBAL_LOGGER_NAME);

    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        // ruleid: crlf-injection-logs
        String param = request.getParameter("param");
        log.info("foo"+param+"bar");
        response.getWriter().append("Served at: ").append(request.getContextPath());
    }
}
