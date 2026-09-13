
package testcode.script;

import javax.el.ELContext;
import javax.el.ExpressionFactory;
import javax.el.ValueExpression;
import javax.faces.context.FacesContext;

public class ElExpressionSample {
    // ok: el-injection
    public void safeEL() {
        FacesContext context = FacesContext.getCurrentInstance();
        ExpressionFactory expressionFactory = context.getApplication().getExpressionFactory();
        ELContext elContext = context.getELContext();
        ValueExpression vex = expressionFactory.createValueExpression(elContext, "1+1", String.class);
        String result = (String) vex.getValue(elContext);
        System.out.println(result);
    }
}
