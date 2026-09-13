
package com.company.util;

import org.jboss.seam.log.Logging;
import org.jboss.seam.log.Log;

public class HttpRequestDebugFilter implements Filter {
    Log log = Logging.getLog(HttpRequestDebugFilter.class);

    public void logUser(User user) {
        // ruleid: seam-log-injection
        log.info("Current logged in user : " + user.getUsername());
    }
}
