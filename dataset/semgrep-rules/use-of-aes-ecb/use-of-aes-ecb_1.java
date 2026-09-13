
class AES{
  public void useofAES2() {
    // ruleid: use-of-aes-ecb
    useCipher(Cipher.getInstance("AES/ECB/PKCS5Padding"));
  }
}
