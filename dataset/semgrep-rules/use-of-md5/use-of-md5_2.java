
import org.apache.commons.codec.digest.DigestUtils;

public class Bad{
  public byte[] bad3(String password) {
    // ok: use-of-md5
    byte[] hashValue = DigestUtils.getMd5Digest().digest(password.getBytes());
    return hashValue;
  }
}
