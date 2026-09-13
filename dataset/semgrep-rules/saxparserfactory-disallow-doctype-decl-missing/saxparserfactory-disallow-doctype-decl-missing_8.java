
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class OneMoreGoodSAXParserFactory {
    public void GoodSAXParserFactory(boolean condition) throws  ParserConfigurationException {
        SAXParserFactory spf = null;
        
        if ( condition ) {
            spf = SAXParserFactor.newInstance();
        } else {
            spf = newFactory();
        }
        spf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        //ok:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }

    private SAXParserFactory newFactory(){
        return SAXParserFactory.newInstance();
    }
}
