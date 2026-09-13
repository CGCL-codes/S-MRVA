
@RestController
public class SecurityQuestionAssignment extends AssignmentEndpoint {

  @PostMapping("/PasswordReset/SecurityQuestions")
  @ResponseBody
  public AttackResult completed(@RequestParam String question) {
    var answer = of(questions.get(question));
    if (answer.isPresent()) {
      triedQuestions.incr(question);
      if (triedQuestions.isComplete()) {
        //ok: tainted-html-string
        return success(this).output("<b>" + answer + "</b>").build();
      }
    }
    return informationMessage(this)
        .feedback("password-questions-one-successful")
        .output(answer.orElse("Unknown question, please try again..."))
        .build();
  }
}
