
import org.apache.commons.codec.digest.DigestUtils;

public class Bad{
  public byte[] ok(String password) {
    // ok: use-of-md5-digest-utils
    byte[] hashValue = DigestUtils.getSha512Digest().digest(password.getBytes());
    return hashValue;
  }
}
