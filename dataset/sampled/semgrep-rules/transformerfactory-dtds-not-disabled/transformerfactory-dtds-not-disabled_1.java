
package example;

import javax.xml.transform.TransformerFactory;

class TransformerFactory {
    public void GoodTransformerFactory2() {
        TransformerFactory factory = TransformerFactory.newInstance();
        //ok:transformerfactory-dtds-not-disabled
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_STYLESHEET, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.newTransformer(new StreamSource(xyz));
    }
}
