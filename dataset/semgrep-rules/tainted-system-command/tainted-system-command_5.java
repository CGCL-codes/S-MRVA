
class CommandInjection {
    public static void test3(@RequestParam String input) {
        StringBuilder stringBuilder = new StringBuilder(100);
        stringBuilder.append(input);
        stringBuilder.append("test2");
        Runtime rt = Runtime.getRuntime();
        // ruleid: tainted-system-command
        Process exec = rt.exec(stringBuilder);
    }
}
