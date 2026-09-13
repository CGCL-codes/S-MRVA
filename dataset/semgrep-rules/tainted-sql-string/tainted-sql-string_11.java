
package com.r2c.tests;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

@RestController
@EnableAutoConfiguration
public class TestController {

    @RequestMapping(value = "/testok6", method = RequestMethod.POST, produces = "plain/text")
    ResultSet ok6(@RequestBody String name) {
        String sql = "SELECT * FROM table WHERE name = ";
        // ok: tainted-sql-string
        sql += ("hello".substring(2,3) == name.substring(2,3)) + ";";
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:8080", "guest", "password");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.execute(sql);
        return rs;
    }
}
