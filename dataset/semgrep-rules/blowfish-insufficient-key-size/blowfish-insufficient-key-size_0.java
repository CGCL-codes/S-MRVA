
import java.util.regex.Pattern;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletRequestWrapper;

public class Cls {
    public void unsafeKeySize() {
        // ruleid: blowfish-insufficient-key-size
        KeyGenerator keyGen = KeyGenerator.getInstance("Blowfish");
        keyGen.init(64);
    }
}
