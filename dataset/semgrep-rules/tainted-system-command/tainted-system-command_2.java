
class CommandInjection {
    public ResponseEntity<GenericVulnerabilityResponseBean<String>> getVulnerablePayloadLevel2(
            @RequestParam(IP_ADDRESS) String ipAddress, RequestEntity<String> requestEntity)
            throws ServiceApplicationException, IOException {

        Supplier<Boolean> validator =
                () ->
                        StringUtils.isNotBlank(ipAddress)
                                && !SEMICOLON_SPACE_LOGICAL_AND_PATTERN
                                        .matcher(requestEntity.getUrl().toString())
                                        .find();
        return new ResponseEntity<GenericVulnerabilityResponseBean<String>>(
                new GenericVulnerabilityResponseBean<String>(
                        // todoruleid: tainted-system-command
                        // Indirection, needs interproc taint
                        this.getResponseFromPingCommand(ipAddress, validator.get()).toString(),
                        true),
                HttpStatus.OK);
    }
}
