
package testcode.sqli.turbine;

import org.apache.turbine.om.security.peer.GroupPeer;

public class TurbineSql {
    public void injection2(GroupPeer peer2, String injection) {
        // ruleid: turbine-sqli
        peer2.executeQuery(injection,0,0,"",false);
    }
}
