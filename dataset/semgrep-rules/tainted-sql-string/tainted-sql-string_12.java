
package com.r2c.tests;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

class Bar {
  int x;

  public int getX() {
    return x;
  }
}

class Foo {
  List<Bar> bars;

  public List<Bar> getBars(String name) {
    return bars;
  }
}

class Test {
  @RequestMapping(value = "/testok6", method = RequestMethod.POST, produces = "plain/text")
  public ResultSet ok7(@RequestBody String name, Foo foo) {
        var v = foo.getBars(name).get(0).getX();
        String sql = "SELECT * FROM table WHERE name = ";
        // ruleid: deepok: tainted-sql-string
        sql += v + ";";
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:8080", "guest", "password");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.execute(sql);
        return rs;
  }
}
