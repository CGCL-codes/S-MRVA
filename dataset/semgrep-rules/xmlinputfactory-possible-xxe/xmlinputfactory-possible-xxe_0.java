
package example;

import javax.xml.stream.XMLInputFactory;

class GoodXMLInputFactory {
    public void blah() {
        final XMLInputFactory xmlInputFactory = XMLInputFactory.newFactory();

        // See
        // https://github.com/OWASP/CheatSheetSeries/blob/master/cheatsheets/XML_External_Entity_Prevention_Cheat_Sheet.md#xmlinputfactory-a-stax-parser
        xmlInputFactory.setProperty(XMLInputFactory.SUPPORT_DTD, false);
        // ok
        xmlInputFactory.setProperty("javax.xml.stream.isSupportingExternalEntities", false);
    }
}
