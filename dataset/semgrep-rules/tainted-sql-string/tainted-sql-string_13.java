
package com.r2c.tests;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

@Getter
@Setter
public class SiteModel {
	private List<PrefixSiteIds> prefixes;
    public List<PrefixSiteIds> getPrefixes(String name) {
        return prefixes;
    }
}

@Getter
@Setter
public class PrefixSiteIds {
	public SiteIds sites;
}

@Getter
@Setter
public class SiteIds {
	public Set<Integer> ids = new HashSet<>();
}

class Test2 {
  @RequestMapping(value = "/testok8", method = RequestMethod.POST, produces = "plain/text")
  public ResultSet ok8(@RequestBody String name, SiteModel sitemodel) {
        var v = sitemodel.getPrefixes(name).sites.ids.get(0);
        String sql = "SELECT * FROM table WHERE name = ";
        // ruleid: deepok: tainted-sql-string
        sql += v + ";";
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:8080", "guest", "password");
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.execute(sql);
        return rs;
  }
}
