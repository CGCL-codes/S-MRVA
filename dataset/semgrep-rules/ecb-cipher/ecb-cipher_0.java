
class ECBCipher {
  public void ecbCipher() {
    // ruleid: ecb-cipher
    Cipher c = Cipher.getInstance("AES/ECB/NoPadding");
    c.init(Cipher.ENCRYPT_MODE, k, iv);
    byte[] cipherText = c.doFinal(plainText);
  }
}
