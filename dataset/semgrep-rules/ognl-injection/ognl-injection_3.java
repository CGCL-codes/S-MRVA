
package testcode.script.ognl;

import com.opensymphony.xwork2.ognl.OgnlReflectionProvider;

import javax.management.ReflectionException;
import java.beans.IntrospectionException;
import java.util.HashMap;
import java.util.Map;

public class OgnlReflectionProviderSample {

    // ruleid: ognl-injection
    public void unsafeOgnlReflectionProvider3(String input, OgnlTextParser reflectionProvider) throws IntrospectionException, ReflectionException {
        reflectionProvider.evaluate( input );
    }
}
