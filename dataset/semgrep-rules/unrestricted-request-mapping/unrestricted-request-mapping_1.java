
@Controller
public class Controller {

    // ruleid: unrestricted-request-mapping
    @RequestMapping(value = "/path")
    public void writeData2() {
        // State-changing operations performed within this method.
    }
}
