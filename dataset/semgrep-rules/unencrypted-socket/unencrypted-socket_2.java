
package testcode.crypto;

import javax.net.ssl.SSLServerSocketFactory;
import java.io.*;
import java.net.InetAddress;
import java.net.Socket;
import java.net.ServerSocket;

public class UnencryptedSocket {

    static void otherConstructors() throws IOException {
        // ruleid: unencrypted-socket
        Socket soc1 = new Socket("www.google.com", 80, true);
        doGetRequest(soc1);
        byte[] address = {127, 0, 0, 1};
        // ruleid: unencrypted-socket
        Socket soc2 = new Socket("www.google.com", 80, InetAddress.getByAddress(address), 13337);
        doGetRequest(soc2);
        byte[] remoteAddress = {74, 125, (byte) 226, (byte) 193};
        // ruleid: unencrypted-socket
        Socket soc3 = new Socket(InetAddress.getByAddress(remoteAddress), 80);
        doGetRequest(soc2);
    }

    static void doGetRequest(Socket soc) throws IOException {
        System.out.println("");
        soc.close();
    }
}
