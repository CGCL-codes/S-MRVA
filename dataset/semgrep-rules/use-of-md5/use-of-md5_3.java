
import java.security.MessageDigest;

public class Bad{
  public void bad4() {
      // ruleid: use-of-md5
      java.security.MessageDigest md = java.security.MessageDigest.getInstance("MD5");
      byte[] input = {(byte) '?'};
      Object inputParam = param;
      if (inputParam instanceof String) input = ((String) inputParam).getBytes();
      if (inputParam instanceof java.io.InputStream) {
          byte[] strInput = new byte[1000];
          int i = ((java.io.InputStream) inputParam).read(strInput);
          if (i == -1) {
              response.getWriter()
                      .println(
                              "This input source requires a POST, not a GET. Incompatible UI for the InputStream source.");
              return;
          }
          input = java.util.Arrays.copyOf(strInput, i);
      }
      md.update(input);

      byte[] result = md.digest();
  }
}
