
@Controller
@RequestMapping("/api/test")
public class TestController {

    @RequestMapping(value = "/{name}", method = RequestMethod.POST)
    @PreAuthorize(Permissions.USER)
    @ResponseBody
    public void load(@PathVariable final String name, HttpServletResponse response) throws APIException {
        // ruleid:http-response-splitting
        Cookie cookie = new Cookie("author", name);
        response.addCookie(cookie);
    }
}
