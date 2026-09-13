
@RestController
public class MyController {
    private ObjectMapper objectMapper;

    @PostConstruct
    public void initialize() {
        objectMapper = new ObjectMapper();
        objectMapper.enableDefaultTyping();
    }

    @RequestMapping(path = "/vulnerable", method = RequestMethod.GET, produces = MediaType.APPLICATION_JSON_VALUE)
    public GenericUser vulnerable(@CookieValue(name = "token", required = false) String token)
            throws JsonParseException, JsonMappingException, IOException {
        byte[] decoded = Base64.getDecoder().decode(token);
        String decodedString = new String(decoded);
        // ruleid: jackson-unsafe-deserialization
        Car obj = objectMapper.readValue(
                decodedString,
                Car.class);
        return obj;
    }
}
