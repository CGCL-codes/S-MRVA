
package example;

import javax.xml.transform.TransformerFactory;

class TransformerFactory {
    public void BadTransformerFactory() {
        TransformerFactory factory = TransformerFactory.newInstance();
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        //ruleid:transformerfactory-dtds-not-disabled
        factory.newTransformer(new StreamSource(xyz));
    }
}
