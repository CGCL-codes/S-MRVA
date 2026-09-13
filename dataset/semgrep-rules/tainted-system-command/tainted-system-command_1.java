
class CommandInjection {
    public ResponseEntity<GenericVulnerabilityResponseBean<String>> getVulnerablePayloadLevel1(
            @RequestParam(IP_ADDRESS) String ipAddress) throws IOException {
        Supplier<Boolean> validator = () -> StringUtils.isNotBlank(ipAddress);
        boolean isWindows = System.getProperty("os.name").toLowerCase().startsWith("windows");
        StringBuilder stringBuilder = new StringBuilder();
        if (isValid) {
            Process process;
            if (!isWindows) {
                // ruleid: tainted-system-command
                process =
                        new ProcessBuilder(new String[] {"sh", "-c", "ping -c 2 " + ipAddress})
                                .redirectErrorStream(true)
                                .start();
            } else {
                // ruleid: tainted-system-command
                process =
                        new ProcessBuilder(new String[] {"cmd", "/c", "ping -n 2 " + ipAddress})
                                .redirectErrorStream(true)
                                .start();
            }
            try (BufferedReader bufferedReader =
                    new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                bufferedReader.lines().forEach(val -> stringBuilder.append(val).append("\n"));
            }
        }
        return new ResponseEntity<GenericVulnerabilityResponseBean<String>>(
                new GenericVulnerabilityResponseBean<String>(
                        stringBuilder.toString(),
                        true),
                HttpStatus.OK);
    }
}
