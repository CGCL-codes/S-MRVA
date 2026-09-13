
class CommandInjection {
    public static void test5(@RequestParam String input) {
        String test1 = "test";
        String comb = String.format("%s%s", test1, input);
        Runtime rt = Runtime.getRuntime();
        // ruleid: tainted-system-command
        Process exec = rt.exec(comb);
    }
}
