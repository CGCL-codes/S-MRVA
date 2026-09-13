
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.ParserConfigurationException;

class GoodDocumentBuilderFactory {
    public void GoodSAXParserFactory() throws  ParserConfigurationException {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        //ok:documentbuilderfactory-disallow-doctype-decl-false
        spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    }
}
