
import java.lang.Runtime;

class Cls {
    public void test3(String plainText) {
        // ruleid: no-null-cipher
        useCipher(new NullCipher());
    }

    private static void useCipher(Cipher cipher) throws Exception {
       // sast should complain about the hard-coded key
       SecretKey key = new SecretKeySpec("secret".getBytes("UTF-8"), "AES");
       cipher.init(Cipher.ENCRYPT_MODE, key);
       byte[] plainText  = "aeiou".getBytes("UTF-8");
       byte[] cipherText = cipher.doFinal(plainText);
       System.out.println(new String(cipherText));
    }
}
