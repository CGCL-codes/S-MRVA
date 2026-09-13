
package testcode.xmldecoder;

import java.beans.XMLDecoder;

public class XmlDecodeUtil {

    // ok: xml-decoder
    public static Object handleXml2() {
        String strXml = "<safe>XML</safe>";
        XMLDecoder d = new XMLDecoder(strXml);
        try {
            Object result = d.readObject();
            return result;
        }
        finally {
            d.close();
        }
    }
}
