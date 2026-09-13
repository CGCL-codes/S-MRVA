
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class GoodSAXParserFactoryCtr2 {
    public void somemethod() throws Exception {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        setFeatures(spf);
        //ok:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }

    private void setFeatures(SAXParserFactory spf) throws Exception {
        spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    }
}
