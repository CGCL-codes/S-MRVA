
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class GcmHardcodedIV
{
    public static final int GCM_TAG_LENGTH = 16;
    public static final String BAD_IV = "ab0123456789";

    private static byte[] theIV;
    private static SecretKey theKey;

    public static void setKeys() throws Exception {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
        keyGenerator.init(256);

        theIV = BAD_IV.getBytes();
    }
}
