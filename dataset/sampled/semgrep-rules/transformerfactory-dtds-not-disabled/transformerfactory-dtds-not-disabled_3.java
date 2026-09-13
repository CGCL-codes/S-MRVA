
package example;

import javax.xml.transform.TransformerFactory;

class TransformerFactory {
    public void GoodTransformerFactory4() {
        TransformerFactory factory = TransformerFactory.newInstance();
        //ok:transformerfactory-dtds-not-disabled
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalDTD", "");
        factory.setAttribute("http://javax.xml.XMLConstants/property/accessExternalStylesheet", "");
        factory.newTransformer(new StreamSource(xyz));
    }
}
