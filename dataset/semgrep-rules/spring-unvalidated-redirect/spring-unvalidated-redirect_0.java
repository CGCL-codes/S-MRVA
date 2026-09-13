
package testcode.spring;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

@Controller
public class SpringUnvalidatedRedirectController {

    // ruleid: spring-unvalidated-redirect
    @RequestMapping("/redirect1")
    public String redirect1(@RequestParam("url") String url) {
        return "redirect:" + url;
    }
}
