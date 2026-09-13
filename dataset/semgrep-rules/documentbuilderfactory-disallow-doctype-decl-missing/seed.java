package example;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.ParserConfigurationException;

class BadDocumentBuilderFactory{
    public void BadDocumentBuilderFactory() throws  ParserConfigurationException {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        //ruleid:documentbuilderfactory-disallow-doctype-decl-missing
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.newDocumentBuilder();
    }

    public void BadDocumentBuilderFactory2() throws  ParserConfigurationException {
        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        dbf.setFeature("somethingElse", true);
        //ruleid:documentbuilderfactory-disallow-doctype-decl-missing
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.newDocumentBuilder();
    }
}

class BadDocumentBuilderFactoryStatic {

    private static DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();

    static {
        dbf.setFeature("not-a-secure-feature", true);
    }

    public void doSomething(){
        //ruleid:documentbuilderfactory-disallow-doctype-decl-missing
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.newDocumentBuilder();
    }

}


class OneMoreBadDocumentBuilderFactory {

    public void GoodDocumentBuilderFactory(boolean condition) throws  ParserConfigurationException {
        DocumentBuilderFactory dbf = null;
        
        if ( condition ) {
            dbf = DocumentBuilderFactory.newInstance();
        } else {
            dbf = newFactory();
        }
        //ruleid:documentbuilderfactory-disallow-doctype-decl-missing
        dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        dbf.newDocumentBuilder();
    }

    private DocumentBuilderFactory newFactory(){
        return DocumentBuilderFactory.newInstance();
    }


}