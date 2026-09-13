
package unsafe.jaxrs;

import java.util.*;
import javax.ws.rs.*;
import javax.ws.rs.core.*;

@Path("/")
@Consumes(MediaType.APPLICATION_JSON)
@Produces(MediaType.APPLICATION_JSON)
public class PoC_resource {
  // ok: default-resteasy-provider-abuse
  @POST
  @Path("/concat")
  public Map<String, String> doConcat(Pair pair) {
    HashMap<String, String> result = new HashMap<String, String>();
    result.put("Result", pair.getP1() + pair.getP2());
    return result;
  }
}
