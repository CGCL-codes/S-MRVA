
package testcode.sqli.turbine;

import org.apache.turbine.om.security.peer.GroupPeer;

public class TurbineSql {
    public void injection4(String injection) {
        // ruleid: turbine-sqli
        GroupPeer.executeQuery(injection,false,null);
    }
}
