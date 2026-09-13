
package com.r2c.tests;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

@RestController
@EnableAutoConfiguration
public class TestController {

    @RequestMapping(value = "/test4", method = RequestMethod.POST, produces = "plain/text")
    ResultSet test4(@RequestBody String name) {
        StringBuilder sql = new StringBuilder("SELECT * FROM table WHERE name = ");
        // ruleid: tainted-sql-string
        sql.append(name + ";");
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:8080", "guest", "password");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.execute(sql.toString());
        return rs;
    }
}
