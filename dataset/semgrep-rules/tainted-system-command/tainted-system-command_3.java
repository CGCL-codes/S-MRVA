
class CommandInjection {
    public static void test1(@RequestParam(IP_ADDRESS) String ipAddress) {
        String args = "ping -c 2 " + ipAddress + "test";
        Process process;
        process = new ProcessBuilder(new String[] {"sh", "-c", args});
        // ruleid: tainted-system-command
        process.start();
    }
}
