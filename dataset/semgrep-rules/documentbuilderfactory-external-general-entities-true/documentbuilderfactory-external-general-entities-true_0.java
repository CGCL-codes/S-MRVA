
package example;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

class GoodDocumentBuilderFactory {
    public void GoodXMLInputFactory() throws  ParserConfigurationException {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        //ok:documentbuilderfactory-external-general-entities-true
        dbf.setFeature("http://xml.org/sax/features/external-general-entities" , false);
    }
}
