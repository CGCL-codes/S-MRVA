
public class RandomIV {

    public RandomIV() {
        // ok: no-static-initialization-vector
        byte[] iv = new byte[16];
        new SecureRandom().nextBytes(iv);

        IvParameterSpec staticIvSpec = new IvParameterSpec(iv); // IvParameterSpec initialized using its own randomizer.

        c.init(Cipher.ENCRYPT_MODE, skeySpec, staticIvSpec, new SecureRandom());
    }
}
