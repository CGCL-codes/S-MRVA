
package unsafe.jaxrs;

import java.util.*;
import javax.ws.rs.*;
import javax.ws.rs.core.*;

@Path("/")
public class PoC_resource {
  @POST
  @Path("/count")
  @Produces(MediaType.APPLICATION_JSON)
  // ok: insecure-resteasy-deserialization
  @Consumes(MediaType.APPLICATION_JSON)
  public Map<String, Integer> doCount(ArrayList<Object> elements) {
    HashMap<String, Integer> result = new HashMap<String, Integer>();
    result.put("Result", elements.size());

    return result;
  }
}
