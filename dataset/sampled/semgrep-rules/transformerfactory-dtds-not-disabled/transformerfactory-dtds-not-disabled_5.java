
package example;

import javax.xml.transform.TransformerFactory;

class TransformerFactory {
    public void BadTransformerFactory2() {
        TransformerFactory factory = TransformerFactory.newInstance();
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "");
        //ruleid:transformerfactory-dtds-not-disabled
        factory.newTransformer(new StreamSource(xyz));
    }
}
