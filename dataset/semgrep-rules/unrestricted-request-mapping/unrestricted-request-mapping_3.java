
@Controller
public class Controller {

    /**
     * For state-changing methods use either
     * RequestMethod.POST, RequestMethod.PUT, RequestMethod.DELETE, or RequestMethod.PATCH.
     */
    // ok: unrestricted-request-mapping
    @RequestMapping(value = "/path", method = RequestMethod.POST)
    public void writeData3() {
        // State-changing operations performed within this method.
    }
}
