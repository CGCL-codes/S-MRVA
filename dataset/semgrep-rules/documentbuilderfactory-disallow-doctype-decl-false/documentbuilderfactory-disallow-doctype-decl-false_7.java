
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.ParserConfigurationException;

class BadSAXParserFactory {
    public void BadSAXParserFactory() throws  ParserConfigurationException {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        //ruleid:documentbuilderfactory-disallow-doctype-decl-false
        spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", false);
        //fix:documentbuilderfactory-disallow-doctype-decl-false
        //spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    }
}
