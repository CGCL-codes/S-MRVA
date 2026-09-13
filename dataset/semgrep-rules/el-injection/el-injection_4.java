
package testcode.script;

public class ElExpressionSample {
    // ruleid: el-injection
    private void unsafeELTemplate(String message, ConstraintValidatorContext context) {
         context.disableDefaultConstraintViolation();
         context
             .someMethod()
             .buildConstraintViolationWithTemplate(message)
             .addConstraintViolation();
    }
}
