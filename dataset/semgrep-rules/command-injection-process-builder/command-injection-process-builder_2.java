
public class TestExecutor {
    public String test3(String userInput) {
      ProcessBuilder builder = new ProcessBuilder();
      // ruleid: command-injection-process-builder
      builder.command("bash", "-c", userInput);
      return "foo";
    }
}
