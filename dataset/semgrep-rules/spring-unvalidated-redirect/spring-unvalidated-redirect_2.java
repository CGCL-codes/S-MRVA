
package testcode.spring;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

@Controller
public class SpringUnvalidatedRedirectController {

    @RequestMapping("/redirect3")
    public String redirect3(@RequestParam("url") String url) {
        return buildRedirect(url);
    }

    // ruleid: spring-unvalidated-redirect
    private String buildRedirect(String u) {
        return "redirect:" + u;
    }
}
