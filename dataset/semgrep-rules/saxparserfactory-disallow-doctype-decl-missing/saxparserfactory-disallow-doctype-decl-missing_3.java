
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class GoodSAXParserFactory {
    public void GoodSAXParserFactory4() throws  ParserConfigurationException {
        SAXParserFactory factory = XmlUtils.getSecureSAXParserFactory();
        //Deep semgrep could find issues like this
        //ok:saxparserfactory-disallow-doctype-decl-missing
        saxparser = factory.newSAXParser();
    }
}
