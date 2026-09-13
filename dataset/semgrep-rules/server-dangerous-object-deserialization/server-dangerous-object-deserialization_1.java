
package de.mogwailabs.BSidesRMIService;

import java.rmi.Remote;
import java.rmi.RemoteException;

// ruleid:server-dangerous-object-deserialization
public interface IBSidesService extends Remote {
   boolean registerTicket(String ticketID) throws RemoteException;
   void vistTalk(String talkID) throws RemoteException;
   void poke(StringBuilder attende) throws RemoteException;
}
