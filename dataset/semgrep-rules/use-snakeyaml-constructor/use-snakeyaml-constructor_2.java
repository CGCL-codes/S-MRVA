
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.Constructor;

public class SnakeYamlTestCase {
    public void customConstructorLoad(String toLoad, Class goodClass) {
        // ok:use-snakeyaml-constructor
        Yaml yaml = new Yaml(new Constructor(goodClass));
        yaml.load(toLoad);
    }
}
