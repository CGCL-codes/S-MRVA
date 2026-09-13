
package testcode.sqli.turbine;

import org.apache.turbine.om.peer.BasePeer;

public class TurbineSql {
    public void injection111(BasePeer peer1, String injection) {
        // ruleid: turbine-sqli
        peer1.executeQuery(injection,0,0,false,null);
    }
}
