
package example;

import javax.xml.stream.XMLInputFactory;
import static javax.xml.stream.XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES;

class BadXMLInputFactory2 {
    public BadXMLInputFactory2() {
        // ruleid:xmlinputfactory-possible-xxe
        final XMLInputFactory xmlInputFactory = XMLInputFactory.newFactory();
        xmlInputFactory.setProperty(IS_SUPPORTING_EXTERNAL_ENTITIES, true);
    }
}
