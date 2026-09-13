
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
    //It has not been found how to detect hardcoded byte arrays with semgrep
    //todoruleid: gcm-nonce-reuse
    public static final byte[] BAD_IV2 = new byte[]{0,1,2,3,4,5,6,7,8,9,10,11};
}
