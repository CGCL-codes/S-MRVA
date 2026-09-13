
import java.security.KeyPairGenerator;

public class WeakRSA {
  static void rsaOK() {
    // ok: use-of-weak-rsa-key
    KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
    keyGen.initialize(2048);
  }
}
