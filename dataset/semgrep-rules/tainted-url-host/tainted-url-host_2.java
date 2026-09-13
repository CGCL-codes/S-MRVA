
@RestController
@RequestMapping("/user03")
public class User03Controller {

    @Autowired
    private RestTemplate restTemplate;

    @PostMapping("/add")
    public Integer add(UserAddDTO addDTO) {
        // è¯·æ±å¤´
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        // è¯·æ±ä½
        String body = JSON.toJSONString(addDTO);
        // åå»º HttpEntity å¯¹è±¡
        HttpEntity<String> entity = new HttpEntity<>(body, headers);
        // æ§è¡è¯·æ±
        // ok: tainted-url-host
        String url = String.format("http://%s/user/add", "demo-provider");
        return restTemplate.postForObject(url, entity, Integer.class);
    }
}
