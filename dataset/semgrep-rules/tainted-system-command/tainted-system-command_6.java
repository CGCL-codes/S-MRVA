
class CommandInjection {
    public static void test4(@RequestParam String input) {
        String test1 = "test";
        String comb = test1.concat(input);
        Runtime rt = Runtime.getRuntime();
        // ruleid: tainted-system-command
        Process exec = rt.exec(comb);
    }
}
