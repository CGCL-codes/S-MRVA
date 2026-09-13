
package example;

import javax.xml.stream.XMLInputFactory;

class BadXMLInputFactory1 {
    public BadXMLInputFactory1() {
        // ruleid:xmlinputfactory-possible-xxe
        final XMLInputFactory xmlInputFactory = XMLInputFactory.newFactory();
        xmlInputFactory.setProperty("javax.xml.stream.isSupportingExternalEntities", true);
    }
}
