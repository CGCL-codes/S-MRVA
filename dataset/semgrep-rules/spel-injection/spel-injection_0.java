
package testcode.script;

import org.springframework.expression.Expression;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;

public class SpelSample {

    private static PersonDTO TEST_PERSON = new PersonDTO("Benoit", "Doudou");

    // ruleid: spel-injection
    public static void parseExpressionInterface1(String property) {
        ExpressionParser parser = new SpelExpressionParser();
        StandardEvaluationContext testContext = new StandardEvaluationContext(TEST_PERSON);
        Expression exp2 = parser.parseExpression(property+" == 'Benoit'");
        String dynamicValue = exp2.getValue(testContext, String.class);
        System.out.println("exp2="+dynamicValue);
    }
}
