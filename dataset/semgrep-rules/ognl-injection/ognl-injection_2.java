
package testcode.script.ognl;

import com.opensymphony.xwork2.ognl.OgnlReflectionProvider;

import javax.management.ReflectionException;
import java.beans.IntrospectionException;
import java.util.HashMap;
import java.util.Map;

public class OgnlReflectionProviderSample {

    // ruleid: ognl-injection
    public void unsafeOgnlReflectionProvider2(String input, OgnlUtil reflectionProvider) throws IntrospectionException, ReflectionException {
        reflectionProvider.setValue(input, null, null,null);
    }
}
