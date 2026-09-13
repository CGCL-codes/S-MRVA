
@RestController
public class SecurityQuestionAssignment extends AssignmentEndpoint {

  @PostMapping("SecurePasswords/assignment")
  @ResponseBody
  public AttackResult completed2(@RequestParam String password) {
    Zxcvbn zxcvbn = new Zxcvbn();
    StringBuilder output = new StringBuilder();
    DecimalFormat df = new DecimalFormat("0", DecimalFormatSymbols.getInstance(Locale.ENGLISH));
    df.setMaximumFractionDigits(340);
    Strength strength = zxcvbn.measure(password);

    output.append("<b>Your Password: *******</b></br>");
    output.append("<b>Length: </b>" + password.length() + "</br>");
    output.append(
        "<b>Estimated guesses needed to crack your password: </b>"
            + df.format(strength.getGuesses())
            + "</br>");

    if (strength.getScore() >= 4)
        // ok: tainted-html-string
        return success(this).feedback("securepassword-success").output(output.toString()).build();
    // ok: tainted-html-string
    else return failed(this).feedback("securepassword-failed").output(output.toString()).build();
  }
}
