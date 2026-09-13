
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.InputStreamReader;
import java.net.Socket;
import org.springframework.web.bind.annotation.RequestParam;

public static void bad(@RequestParam String user)
{
    Socket sock;
    BufferedReader filenameReader = new BufferedReader(
            new InputStreamReader(sock.getInputStream(), "UTF-8"));
    String filename = filenameReader.readLine();
    // ruleid: tainted-file-path
    BufferedReader fileReader = new BufferedReader(new FileReader("/home/" + user + "/" + filename));
    String fileLine = fileReader.readLine();
    while(fileLine != null) {
            sock.getOutputStream().write(fileLine.getBytes());
            fileLine = fileReader.readLine();
    }
}
