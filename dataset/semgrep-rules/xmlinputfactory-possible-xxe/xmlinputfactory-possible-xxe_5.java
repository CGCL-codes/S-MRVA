
package example;

import javax.xml.stream.XMLInputFactory;

class MaybeBadXMLInputFactory {
    public void foobar() {
        // ruleid:xmlinputfactory-possible-xxe
        final XMLInputFactory xmlInputFactory = XMLInputFactory.newFactory();
    }
}
