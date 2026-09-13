
package example;

import javax.xml.parsers.SAXParserFactory;
import javax.xml.parsers.SAXParser;
import javax.xml.parsers.ParserConfigurationException;

class BadSAXParserFactoryStatic {
    private static SAXParserFactory spf = SAXParserFactory.newInstance();

    static {
        spf.setFeature("not-a-secure-feature", true);
    }

    public void doSomething(){
        //ruleid:saxparserfactory-disallow-doctype-decl-missing
        spf.newSAXParser();
    }
}
