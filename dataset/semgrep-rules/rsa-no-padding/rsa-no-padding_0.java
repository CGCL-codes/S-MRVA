
class RSAPadding {
  public void rsaNoPadding() {
    // ruleid: rsa-no-padding
    Cipher.getInstance("RSA/NONE/NoPadding");
  }
}
