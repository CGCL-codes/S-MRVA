
@RestController
public class SecurePasswordsAssignment extends AssignmentEndpoint {

  @PostMapping("SecurePasswords/assignment")
  @ResponseBody
  public AttackResult completed(@RequestParam String password) {
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
    output.append(
        "<div style=\"float: left;padding-right: 10px;\"><b>Score: </b>"
            + strength.getScore()
            + "/4 </div>");
    if (strength.getScore() <= 1) {
      output.append(
          "<div style=\"background-color:red;width: 200px;border-radius: 12px;float:"
              + " left;\">&nbsp;</div></br>");
    } else if (strength.getScore() <= 3) {
      output.append(
          "<div style=\"background-color:orange;width: 200px;border-radius: 12px;float:"
              + " left;\">&nbsp;</div></br>");
    } else {
      output.append(
          "<div style=\"background-color:green;width: 200px;border-radius: 12px;float:"
              + " left;\">&nbsp;</div></br>");
    }
    output.append(
        "<b>Estimated cracking time: </b>"
            + calculateTime(
                (long) strength.getCrackTimeSeconds().getOnlineNoThrottling10perSecond())
            + "</br>");
    if (strength.getFeedback().getWarning().length() != 0)
      output.append("<b>Warning: </b>" + strength.getFeedback().getWarning() + "</br>");
    output.append("<ul>");
    for (String sug : strength.getFeedback().getSuggestions())
        output.append("<li>" + sug + "</li>");
    output.append("</ul></br>");
    output.append("<b>Score: </b>" + strength.getScore() + "/4 </br>");

    if (strength.getScore() >= 4)
      // ok: tainted-html-string
      return success(this).feedback("securepassword-success").output(output.toString()).build();
    // ok: tainted-html-string
    else return failed(this).feedback("securepassword-failed").output(output.toString()).build();
  }
}
