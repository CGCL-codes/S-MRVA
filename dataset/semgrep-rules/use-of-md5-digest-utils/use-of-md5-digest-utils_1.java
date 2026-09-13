
import org.apache.commons.codec.digest.DigestUtils;

public class Bad{
  public byte[] bad2(String password) {
    // ruleid: use-of-md5-digest-utils
    byte[] hashValue = DigestUtils.getMd5Digest().digest(password.getBytes());
    return hashValue;
  }
}
