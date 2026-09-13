
package com.r2c.tests;

@RestController
@EnableAutoConfiguration
public class TestController {

    @RequestMapping(value = "/test5", method = RequestMethod.POST, produces = "plain/text")
    ResultSet test5(@RequestBody String name) {
        try {
            // ok: tainted-sql-string
            throw new Exception(String.format("Update request from %s to %s isn't allowed",
            name, bar
            ));
        }
        catch (NullPointerException e) {
            System.out.println("Caught inside fun().");
            throw e; // rethrowing the exception
        }
    }
}
