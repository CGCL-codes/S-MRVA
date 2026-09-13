
class Car {
    public static void anotherMain2(String[] args) throws JsonGenerationException, JsonMappingException, IOException {
        ObjectMapper objectMapper = new ObjectMapper();

        try {
            // ok: jackson-unsafe-deserialization
            Car car = objectMapper.readValue(Paths.get("target/payload.json").toFile(), Another.class);
            System.out.println((car.getColor()));
        } catch (Exception e) {
            System.out.println("Exception raised:" + e.getMessage());
        }
    }
}
