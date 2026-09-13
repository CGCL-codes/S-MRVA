
package testcode.script;

import javax.el.ELContext;
import javax.el.ExpressionFactory;

public class ElExpressionSample {
    // ok: el-injection
    public void safeELMethod(ELContext elContext, ExpressionFactory expressionFactory) {
        expressionFactory.createMethodExpression(elContext, "1+1", String.class, new Class[]{Integer.class});
    }
}
