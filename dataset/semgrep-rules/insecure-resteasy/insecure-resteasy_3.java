
package unsafe.jaxrs;

import java.util.*;
import javax.ws.rs.*;
import javax.ws.rs.core.*;

@Path("/")
public class PoC_resource {
  // ok: default-resteasy-provider-abuse
  @GET
  @Path("/tenantmode")
  @Produces(MediaType.TEXT_PLAIN)
  public String getTenantMode() {
    return kubernetesService.getMessage();
  }
}
