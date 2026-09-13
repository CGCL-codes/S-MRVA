
public class TestExecutor {
    public String test4(String userInput) {
      ProcessBuilder builder = new ProcessBuilder();
      // ruleid: command-injection-process-builder
      builder.command("cmd", "/c", userInput);
      return "foo";
    }
}
