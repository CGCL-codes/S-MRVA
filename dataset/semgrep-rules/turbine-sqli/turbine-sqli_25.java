
package testcode.sqli.turbine;

import org.apache.turbine.om.peer.BasePeer;

public class TurbineSql {
    public void falsePositive(BasePeer peer0) {
        String constantValue = "SELECT * FROM test";
        // ok: turbine-sqli
        peer0.executeQuery(constantValue,false,null);
    }
}
