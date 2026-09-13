
class Car {
    public static void main(String[] args) throws JsonGenerationException, JsonMappingException, IOException {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.enableDefaultTyping();

        try {
            // ruleid: jackson-unsafe-deserialization
            Car car = objectMapper.readValue(Paths.get("target/payload.json").toFile(), Car.class);
            System.out.println((car.getColor()));
        } catch (Exception e) {
            System.out.println("Exception raised:" + e.getMessage());
        }
    }
}
