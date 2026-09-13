
package testcode.crypto;

import javax.net.ssl.SSLServerSocketFactory;
import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.ServerSocket;

public class UnencryptedServerSocket {

    static void plainServerSocket() throws IOException {
        // ruleid: unencrypted-socket
        ServerSocket ssoc = new ServerSocket(1234);
        ssoc.close();
    }
}
