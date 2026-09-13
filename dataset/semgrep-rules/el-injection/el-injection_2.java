
package testcode.script;

import javax.el.ELContext;
import javax.el.ExpressionFactory;

public class ElExpressionSample {
    // ruleid: el-injection
    public void unsafeELMethod(ELContext elContext, ExpressionFactory expressionFactory, String expression) {
        expressionFactory.createMethodExpression(elContext, expression, String.class, new Class[]{Integer.class});
    }
}
