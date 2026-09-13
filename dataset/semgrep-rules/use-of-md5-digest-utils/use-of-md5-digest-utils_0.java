
import java.security.MessageDigest;

public class Bad{
  public byte[] bad1(String password) {
    // ok: use-of-md5-digest-utils
    MessageDigest md5Digest = MessageDigest.getInstance("MD5");
    md5Digest.update(password.getBytes());
    byte[] hashValue = md5Digest.digest();
    return hashValue;
  }
}
