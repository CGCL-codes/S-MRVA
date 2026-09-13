
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class OneMoreBadSAXParserFactory {
    public void GoodSAXParserFactory(boolean condition) throws  ParserConfigurationException {
        SAXParserFactory spf = null;
        
        if ( condition ) {
            spf = SAXParserFactory.newInstance();
        } else {
            spf = newFactory();
        }
        //ruleid:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }

    private SAXParserFactory newFactory(){
        return SAXParserFactory.newInstance();
    }
}
