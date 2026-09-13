
public class TestExecutor {
    private Pair<Integer, String> test1(String command, Logger logAppender) throws IOException {
      String[] cmd = new String[3];
      String osName = System.getProperty("os.name");
      if (osName.startsWith("Windows")) {
          cmd[0] = "cmd.exe";
          cmd[1] = "/C";
      } else {
          cmd[0] = "/bin/bash";
          cmd[1] = "-c";
      }
      cmd[2] = command;

      // ruleid: command-injection-process-builder
      ProcessBuilder builder = new ProcessBuilder(cmd);
      builder.redirectErrorStream(true);
      Process proc = builder.start();
      return Pair.newPair(1, "Killed");
    }
}
