
package testcode.crypto;

import javax.net.ssl.SSLServerSocketFactory;
import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.ServerSocket;

public class UnencryptedSocket {

    static void plainSocket() throws IOException {
        // ruleid: unencrypted-socket
        Socket soc = new Socket("www.google.com", 80);
        doGetRequest(soc);
    }

    static void doGetRequest(Socket soc) throws IOException {
        System.out.println("");
        soc.close();
    }
}
