
package testcode.file.permissions;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermission;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.HashSet;
import java.util.Set;

public class FileApi {

    public static void notOk() throws IOException {
        // ruleid:overly-permissive-file-permission
        Files.setPosixFilePermissions(Paths.get("/var/opt/configuration.xml"), PosixFilePermissions.fromString("rw-rw-r--"));
    }
}
