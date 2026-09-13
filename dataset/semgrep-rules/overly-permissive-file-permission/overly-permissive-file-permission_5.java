
package testcode.file.permissions;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;

public class FileApi {

    public static void ok() throws IOException {
        Files.setPosixFilePermissions(Paths.get("/var/opt/configuration.xml"), PosixFilePermissions.fromString("rw-rw----"));
    }
}
