
package testcode.sqli.turbine;

import org.apache.turbine.om.peer.BasePeer;

public class TurbineSql {
    public void injection3(String injection) {
        // ruleid: turbine-sqli
        BasePeer.executeQuery(injection,"");
    }
}
