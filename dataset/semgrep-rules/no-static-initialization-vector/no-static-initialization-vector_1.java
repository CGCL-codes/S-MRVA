
// ruleid: no-static-initialization-vector
public class StaticIV2 {
    // ruleid: no-static-initialization-vector
    byte[] iv = {
        (byte) 0, (byte) 0, (byte) 0, (byte) 0,
        (byte) 0, (byte) 0, (byte) 0, (byte) 0,
        (byte) 0, (byte) 0, (byte) 0, (byte) 0,
        (byte) 0, (byte) 0, (byte) 0, (byte) 0
    };


    public StaticIV2() {
        IvParameterSpec staticIvSpec = new IvParameterSpec(iv);

        c.init(Cipher.ENCRYPT_MODE, skeySpec, staticIvSpec, new SecureRandom());
    }
}
