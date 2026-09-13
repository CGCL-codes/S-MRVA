
import java.util.regex.Pattern;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletRequestWrapper;

public class Cls {
    public void superSafeKeySize() {
        // ok: blowfish-insufficient-key-size
        KeyGenerator keyGen = KeyGenerator.getInstance("Blowfish");
        keyGen.init(448);
    }
}
