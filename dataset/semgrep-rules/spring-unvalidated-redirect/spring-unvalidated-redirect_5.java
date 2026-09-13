
package testcode.spring;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

@Controller
public class SpringUnvalidatedRedirectController {

    // ok: spring-unvalidated-redirect
    @RequestMapping("/redirectfp")
    public String redirectfp() {
        return "redirect:/";
    }
}
