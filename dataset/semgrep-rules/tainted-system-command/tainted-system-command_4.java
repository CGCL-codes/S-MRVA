
class CommandInjection {
    public static void test2(@RequestParam String input) {
        String latlonCoords = input;
        Runtime rt = Runtime.getRuntime();
        // ok: tainted-system-command
        Process exec = rt.exec(new String[] {
                "c:\\path\to\latlon2utm.exe",
                latlonCoords }); // safe bc args are seperated
    }
}
