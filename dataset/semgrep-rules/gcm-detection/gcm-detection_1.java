
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.util.Base64;

public class GcmHardcodedIV {
    public static final int GCM_TAG_LENGTH = 16;

    private static byte[] theIV;
    private static SecretKey theKey;

    public static String decrypt(String cipherText) throws Exception {
        // ruleid:gcm-detection
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        SecretKeySpec keySpec = new SecretKeySpec(theKey.getEncoded(), "AES");

        // ruleid:gcm-detection
        GCMParameterSpec gcmParameterSpec = new GCMParameterSpec(GCM_TAG_LENGTH * 8, theIV);
        cipher.init(Cipher.DECRYPT_MODE, keySpec, gcmParameterSpec);

        byte[] decoded = Base64.getDecoder().decode(cipherText);
        byte[] decryptedText = cipher.doFinal(decoded);

        return new String(decryptedText);
    }
}
