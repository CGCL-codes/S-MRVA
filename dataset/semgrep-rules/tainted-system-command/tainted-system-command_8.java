
class CommandInjection {
    public static String run(@RequestParam(defaultValue = "I love Linux!") String input) {
        ProcessBuilder processBuilder = new ProcessBuilder();
        String cmd = "/usr/games/cowsay '" + input + "'";
        System.out.println(cmd);
        // ruleid: tainted-system-command
        processBuilder.command("bash", "-c", cmd);
    
        StringBuilder output = new StringBuilder();
    
        try {
          Process process = processBuilder.start();
          BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
    
          String line;
          while ((line = reader.readLine()) != null) {
            output.append(line + "\n");
          }
        } catch (Exception e) {
          e.printStackTrace();
        }
        return output.toString();
      }
}
