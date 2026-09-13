
import java.security.MessageDigest;

public class Bad{
  public byte[] good(String password) {
    // ok: use-of-md5
    MessageDigest md5Digest = MessageDigest.getInstance("SHA-512");
    md5Digest.update(password.getBytes());
    byte[] hashValue = md5Digest.digest();
    return hashValue;
  }
}
