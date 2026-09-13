
@Controller
@RequestMapping("/api/test")
public class TestController {

    private Response safe(String name, Response response) {
        // ok:http-response-splitting
        Cookie cookie = new Cookie("author", name);
        response.addCookie(cookie);
        return response;
    }
}
