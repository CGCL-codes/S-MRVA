
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class GoodSAXParserFactory {
    public void GoodSAXParserFactory2() throws  ParserConfigurationException {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        spf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
        spf.setFeature("http://xml.org/sax/features/external-general-entities", false);
        //ok:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }
}
