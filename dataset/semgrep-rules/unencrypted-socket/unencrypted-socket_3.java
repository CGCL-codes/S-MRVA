
package testcode.crypto;

import javax.net.ssl.SSLServerSocketFactory;
import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.ServerSocket;

public class UnencryptedServerSocket {

    static void sslServerSocket() throws IOException {
        // ok: unencrypted-socket
        ServerSocket ssoc = SSLServerSocketFactory.getDefault().createServerSocket(1234);
        ssoc.close();
    }
}
