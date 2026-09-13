
package testcode.xmldecoder;

import java.beans.XMLDecoder;

public class XmlDecodeUtil {

    // ok: xml-decoder
    public static Object handleXml1() {
        XMLDecoder d = new XMLDecoder("<safe>XML</safe>");
        try {
            Object result = d.readObject();
            return result;
        }
        finally {
            d.close();
        }
    }
}
