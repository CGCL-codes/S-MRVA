
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.SafeConstructor;

public class SnakeYamlTestCase {
    public void safeConstructorLoad(String toLoad) {
        // ok:use-snakeyaml-constructor
        Yaml yaml = new Yaml(new SafeConstructor());
        yaml.load(toLoad);
    }
}
