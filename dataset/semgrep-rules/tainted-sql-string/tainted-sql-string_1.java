
package com.r2c.tests;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

@RestController
@EnableAutoConfiguration
public class TestController {

    @RequestMapping(value = "/test2", method = RequestMethod.POST, produces = "plain/text")
    ResultSet test2(@RequestBody String name) {
        // ruleid: tainted-sql-string
        String sql = String.format("SELECT * FROM table WHERE name = %s;", name);
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:8080", "guest", "password");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.execute(sql);
        return rs;
    }
}
