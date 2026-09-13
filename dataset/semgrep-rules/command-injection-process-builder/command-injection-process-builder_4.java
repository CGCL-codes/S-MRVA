
public class TestExecutor {
    public String okTest() {
      ProcessBuilder builder = new ProcessBuilder();
      // ok: command-injection-process-builder
      builder.command("bash", "-c", "ls");
      return "foo";
    }
}
