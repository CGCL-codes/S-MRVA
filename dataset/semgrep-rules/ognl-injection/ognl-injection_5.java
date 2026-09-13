
package testcode.script.ognl;

import com.opensymphony.xwork2.ognl.OgnlReflectionProvider;

import javax.management.ReflectionException;
import java.beans.IntrospectionException;
import java.util.HashMap;
import java.util.Map;

public class OgnlReflectionProviderSample {

    // ok: ognl-injection
    public void safeOgnlReflectionProvider2(OgnlReflectionProvider reflectionProvider, Class type) throws IntrospectionException, ReflectionException {
        reflectionProvider.getField(type, "thisissafe");
    }
}
