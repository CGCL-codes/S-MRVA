
package example;

import javax.xml.transform.TransformerFactory;

class TransformerFactory {
    public void GoodTransformerFactory3() {
        TransformerFactory factory = TransformerFactory.newInstance();
        //ok:transformerfactory-dtds-not-disabled
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalStylesheet", "");
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "");
        factory.newTransformer(new StreamSource(xyz));
    }
}
