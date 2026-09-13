
public class TestExecutor {
    public String test2(String userInput) {
      ProcessBuilder builder = new ProcessBuilder();
      // ruleid: command-injection-process-builder
      builder.command(userInput);
      return "foo";
    }
}
