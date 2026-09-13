
package testcode.spring;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

@Controller
public class SpringUnvalidatedRedirectController {

    // ruleid: spring-unvalidated-redirect
    @RequestMapping("/redirect2")
    public String redirect2(@RequestParam("url") String url) {
        String view = "redirect:" + url;
        return view;
    }
}
