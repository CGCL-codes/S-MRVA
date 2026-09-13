
package example;

import javax.xml.parsers.ParserConfigurationException;

class GoodSAXParserFactory {
    public void GoodSAXParserFactory() throws  ParserConfigurationException {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        //ok:documentbuilderfactory-external-general-entities-true
        spf.setFeature("http://xml.org/sax/features/external-general-entities" , false);
    }
}
