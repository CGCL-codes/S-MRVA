
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

    public static String decrypt(String cipherText) throws Exception {
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        SecretKeySpec keySpec = new SecretKeySpec(theKey.getEncoded(), "AES");

        //Hard to detect that theIV is indeed built from a hardcoded string
        //todoruleid: gcm-nonce-reuse
        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH * 8, theIV);
        cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmParameterSpec);

        byte[] decoded = Base64.getDecoder().decode(cipherText);
        byte[] decryptedText = cipher.doFinal(decoded);

        return new String(decryptedText);
    }
}
