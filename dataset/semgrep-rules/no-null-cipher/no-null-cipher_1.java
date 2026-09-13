
import java.lang.Runtime;

class Cls {
    public void test2(String plainText) {
        // ok: no-null-cipher
        Cipher cipher = Cipher.getInstance("AES/CBC/PKCS5Padding");
        byte[] cipherText = cipher.doFinal(plainText);
        return cipherText;
    }
}
