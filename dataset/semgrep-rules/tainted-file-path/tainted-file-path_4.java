
import org.springframework.core.io.ClassPathResource;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import org.junit.jupiter.api.Test;
import org.springframework.web.bind.annotation.RequestParam;
import static org.junit.jupiter.api.Assertions.assertEquals;

@Test
public void whenResourceAsFile_thenReadSuccessful(@RequestParam String filename) throws IOException {
    // ruleid: tainted-file-path
    File resource = new ClassPathResource("data/employees.dat" + filename).getFile();
    String employees = new String(Files.readAllBytes(resource.toPath()));
    assertEquals("Joe Employee,Jan Employee,James T. Employee", employees);
}
