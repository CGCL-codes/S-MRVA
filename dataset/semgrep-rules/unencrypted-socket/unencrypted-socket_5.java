
package testcode.crypto;

import javax.net.ssl.SSLServerSocketFactory;
import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.ServerSocket;

public class UnencryptedServerSocket {

    static void otherConstructors() throws IOException {
        // ruleid: unencrypted-socket
        ServerSocket ssoc1 = new ServerSocket();
        ssoc1.close();
        // ruleid: unencrypted-socket
        ServerSocket ssoc2 = new ServerSocket(1234, 10);
        ssoc2.close();
        byte[] address = {127, 0, 0, 1};
        // ruleid: unencrypted-socket
        ServerSocket ssoc3 = new ServerSocket(1234, 10, InetAddress.getByAddress(address));
        ssoc3.close();
    }
}
