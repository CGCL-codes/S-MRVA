
package com.r2c.tests;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

@RestController
@EnableAutoConfiguration
public class TestController {

    @RequestMapping(value = "/ok1", method = RequestMethod.POST, produces = "plain/text")
    ResultSet ok1(@RequestBody String name) {
        // ok: tainted-sql-string
        String sql = "SELECT * FROM table WHERE name = 'everyone';";
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:8080", "guest", "password");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.execute(sql);
        return rs;
    }
}
