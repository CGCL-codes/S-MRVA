
import java.lang.Runtime;

class Cls {
    public byte[] test1(String plainText) {
        // ruleid: no-null-cipher
        javax.crypto.NullCipher nullCipher = new javax.crypto.NullCipher();
        // ruleid: no-null-cipher
        Cipher doNothingCihper = new NullCipher();
        //The ciphertext produced will be identical to the plaintext.
        byte[] cipherText = doNothingCihper.doFinal(plainText);
        return cipherText;
    }
}
