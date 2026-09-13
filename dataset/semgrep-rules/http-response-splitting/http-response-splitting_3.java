
@Controller
@RequestMapping("/api/test")
public class TestController {

    @RequestMapping(value = "/{name}/{book}", method = RequestMethod.POST)
    @PreAuthorize(Permissions.USER)
    @ResponseBody
    public void loadBook(@PathVariable final String name, @PathVariable final String book, HttpServletResponse response) throws APIException {
        AuthorObj author = AuthorObj.getAuthor(name, book);
        // ok:http-response-splitting
        Cookie cookie = new Cookie("sess", "1234");
        response.addCookie(cookie);
    }
}
