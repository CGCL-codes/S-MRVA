
class RSAPadding {
  public void rsaNoPadding2() {
    // ruleid: rsa-no-padding
    useCipher(Cipher.getInstance("RSA/None/NoPadding"));
  }
}
