
@Controller
@RequestMapping("/api/test")
public class TestController {

    @RequestMapping(method = RequestMethod.GET)
    @PreAuthorize(Permissions.ADMIN)
    @ResponseBody
    public void list(HttpServletRequest request, HttpServletResponse response) {
        // ruleid:http-response-splitting
        String author = request.getParameter(AUTHOR_PARAMETER);
        Cookie cookie = new Cookie("author", author);
        response.addCookie(cookie);
    }
}
