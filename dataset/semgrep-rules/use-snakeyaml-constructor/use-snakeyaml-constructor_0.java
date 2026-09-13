
import org.yaml.snakeyaml.Yaml;

public class SnakeYamlTestCase {
    public void unsafeLoad(String toLoad) {
        // ruleid:use-snakeyaml-constructor
        Yaml yaml = new Yaml();
        yaml.load(toLoad);
    }
}
