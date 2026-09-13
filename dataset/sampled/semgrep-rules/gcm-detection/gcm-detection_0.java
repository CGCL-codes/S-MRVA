
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class GcmHardcodedIV {
    public static final int GCM_TAG_LENGTH = 16;
    public static final String BAD_IV = "ab0123456789";

    private static byte[] theIV;
    private static SecretKey theKey;

    public static String encrypt(String clearText) throws Exception {
        // ruleid:gcm-detection
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        SecretKeySpec keySpec = new SecretKeySpec(theKey.getEncoded(), "AES");
        byte[] theBadIV = BAD_IV.getBytes();

        // ruleid:gcm-detection
        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH * 8, theBadIV);
        cipher.init(Cipher.ENCRYPT_MODE, keySpec, gcmParameterSpec);

        byte[] cipherText = cipher.doFinal(clearText.getBytes());

        return Base64.getEncoder().encodeToString(cipherText);
    }
}
