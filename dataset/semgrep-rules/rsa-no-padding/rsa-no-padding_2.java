
class RSAPadding {
  public void rsaPadding() {
    // ok: rsa-no-padding
    Cipher.getInstance("RSA/ECB/OAEPWithMD5AndMGF1Padding");
  }
}
