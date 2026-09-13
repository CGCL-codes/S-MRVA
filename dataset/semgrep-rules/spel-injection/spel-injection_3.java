
package testcode.script;

import org.springframework.expression.Expression;
import org.springframework.expression.spel.standard.SpelExpressionParser;

public class SpelSample {

    // ok: spel-injection
    public static void parseSpelExpression4(String property) {
        SpelExpressionParser parser = new SpelExpressionParser();
        Expression exp1 = parser.parseExpression("'safe expression'");
        String constantValue = exp1.getValue(String.class);
        System.out.println("exp1="+constantValue);
    }
}
