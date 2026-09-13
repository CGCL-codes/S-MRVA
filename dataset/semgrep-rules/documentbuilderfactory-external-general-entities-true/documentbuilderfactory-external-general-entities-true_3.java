
package example;

import javax.xml.parsers.ParserConfigurationException;

class BadSAXParserFactory{
    public void BadSAXParserFactory() throws  ParserConfigurationException {
        SAXParserFactory spf = SAXParserFactory.newInstance();
        //ruleid:documentbuilderfactory-external-general-entities-true
        spf.setFeature("http://xml.org/sax/features/external-general-entities" , true);
    }
}
