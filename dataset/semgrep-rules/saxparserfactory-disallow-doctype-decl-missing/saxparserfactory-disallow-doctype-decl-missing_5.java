
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class BadSAXParserFactory {
    public void BadSAXParserFactory2() throws  ParserConfigurationException {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        spf.setFeature("somethingElse", true);
        //ruleid:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }
}
