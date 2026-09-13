
import java.security.MessageDigest;

public class Bad{
  public byte[] bad2(String password) {
    // ruleid: use-of-md5
    MessageDigest md5Digest = MessageDigest.getInstance("md5");
    md5Digest.update(password.getBytes());
    byte[] hashValue = md5Digest.digest();
    return hashValue;
  }
}
