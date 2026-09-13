
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class GoodSAXParserFactoryStatic {
    private static SAXParserFactory spf = SAXParserFactory.newInstance();

    static {
        spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        //ok:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }
}
