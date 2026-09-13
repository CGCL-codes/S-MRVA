
package testcode.script.ognl;

import com.opensymphony.xwork2.ognl.OgnlReflectionProvider;

import javax.management.ReflectionException;
import java.beans.IntrospectionException;
import java.util.HashMap;
import java.util.Map;

public class OgnlReflectionProviderSample {

    // ruleid: ognl-injection
    public void unsafeOgnlReflectionProvider1(String input, ReflectionProvider reflectionProvider) throws IntrospectionException, ReflectionException {
        reflectionProvider.getValue(input, null, null);
    }
}
